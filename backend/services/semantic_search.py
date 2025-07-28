# backend/app/services/semantic_search.py
import os
import pickle
import numpy as np
import time
from typing import List, Dict, Any, Tuple
from sklearn.metrics.pairwise import cosine_similarity

from config import settings
from models.query import SearchQuery, SearchResult, SearchResponse
from models.video import Scene
from utils.embeddings import EmbeddingGenerator
from services.llm_service import LLMService

class SemanticSearchService:
    """
    Advanced semantic search service for educational video content
    Uses RAG-style retrieval with educational context awareness
    """
    
    def __init__(self):
        self.embedding_generator = EmbeddingGenerator()
        self.llm_service = LLMService()
        self.min_similarity = settings.SIMILARITY_THRESHOLD
        
    async def search_scenes(self, query: SearchQuery, video_metadata: Dict[str, Any] = None) -> SearchResponse:
        """
        Main search function that combines semantic similarity with educational context
        """
        start_time = time.time()
        
        # Step 1: Generate query embedding
        query_embedding = await self.embedding_generator.generate_embedding(query.query)
        
        # Step 2: Find similar scenes
        candidate_scenes = await self._find_candidate_scenes(
            query_embedding, 
            query.video_id,
            query.max_results * 2  # Get more candidates for reranking
        )
        
        # Step 3: Rerank with LLM for educational relevance
        ranked_results = await self._rerank_with_llm(query.query, candidate_scenes)
        
        # Step 4: Generate explanations for top results
        final_results = await self._generate_explanations(query.query, ranked_results[:query.max_results])
        
        # Step 5: Generate follow-up suggestions
        suggestions = await self._generate_suggestions(query.query, final_results)
        
        processing_time = time.time() - start_time
        
        return SearchResponse(
            query=query.query,
            results=final_results,
            total_results=len(final_results),
            processing_time=processing_time,
            suggestions=suggestions
        )
    
    async def _find_candidate_scenes(self, query_embedding: List[float], video_id: str = None, max_results: int = 10) -> List[Dict[str, Any]]:
        """Find candidate scenes using cosine similarity"""
        candidates = []
        
        # Search in specific video or all videos
        search_dirs = []
        if video_id:
            video_dir = os.path.join(settings.EMBEDDINGS_DIR, video_id)
            if os.path.exists(video_dir):
                search_dirs.append(video_dir)
        else:
            # Search all videos
            if os.path.exists(settings.EMBEDDINGS_DIR):
                search_dirs = [
                    os.path.join(settings.EMBEDDINGS_DIR, d) 
                    for d in os.listdir(settings.EMBEDDINGS_DIR)
                    if os.path.isdir(os.path.join(settings.EMBEDDINGS_DIR, d))
                ]
        
        # Load and compare embeddings
        for search_dir in search_dirs:
            video_id_from_path = os.path.basename(search_dir)
            
            for embedding_file in os.listdir(search_dir):
                if embedding_file.endswith('.pkl'):
                    try:
                        with open(os.path.join(search_dir, embedding_file), 'rb') as f:
                            embedding_data = pickle.load(f)
                        
                        # Calculate similarity
                        similarity = cosine_similarity(
                            [query_embedding], 
                            [embedding_data['embedding']]
                        )[0][0]
                        
                        if similarity >= self.min_similarity:
                            candidates.append({
                                'video_id': video_id_from_path,
                                'scene_id': embedding_data['scene_id'],
                                'content': embedding_data['content'],
                                'similarity': similarity
                            })
                    
                    except Exception as e:
                        print(f"Error loading embedding {embedding_file}: {str(e)}")
                        continue
        
        # Sort by similarity and return top candidates
        candidates.sort(key=lambda x: x['similarity'], reverse=True)
        return candidates[:max_results]
    
    async def _rerank_with_llm(self, query: str, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use LLM to rerank candidates based on educational relevance"""
        if not candidates:
            return []
        
        # Prepare context for LLM
        candidate_texts = []
        for i, candidate in enumerate(candidates):
            candidate_texts.append(f"{i+1}. {candidate['content']}")
        
        prompt = f"""
        You are an educational content expert. Rank these video segments by their relevance to the student's question: "{query}"
        
        Consider:
        1. Direct relevance to the question
        2. Educational value and clarity
        3. Whether it provides explanation, demonstration, or examples
        4. Completeness of the content for learning
        
        Video segments:
        {chr(10).join(candidate_texts)}
        
        Return only the ranking as a comma-separated list of numbers (e.g., "3,1,5,2,4"):
        """
        
        try:
            ranking_response = await self.llm_service.generate_response(prompt)
            # Parse ranking
            rankings = [int(x.strip()) - 1 for x in ranking_response.strip().split(',') if x.strip().isdigit()]
            
            # Reorder candidates based on LLM ranking
            reranked = []
            for rank in rankings:
                if 0 <= rank < len(candidates):
                    reranked.append(candidates[rank])
            
            # Add any remaining candidates
            used_indices = set(rankings)
            for i, candidate in enumerate(candidates):
                if i not in used_indices:
                    reranked.append(candidate)
            
            return reranked
        
        except Exception as e:
            print(f"LLM reranking failed: {str(e)}")
            return candidates  # Return original order if reranking fails
    
    async def _generate_explanations(self, query: str, candidates: List[Dict[str, Any]]) -> List[SearchResult]:
        """Generate educational explanations for search results"""
        results = []
        
        for candidate in candidates:
            # Load scene metadata (in production, this would come from database)
            scene_data = await self._load_scene_metadata(candidate['video_id'], candidate['scene_id'])
            
            if not scene_data:
                continue
            
            # Generate explanation using LLM
            explanation = await self._generate_scene_explanation(query, candidate['content'])
            
            result = SearchResult(
                scene_id=candidate['scene_id'],
                video_id=candidate['video_id'],
                video_title=scene_data.get('video_title', 'Educational Video'),
                scene=Scene(
                    id=candidate['scene_id'],
                    start_time=scene_data.get('start_time', 0),
                    end_time=scene_data.get('end_time', 30),
                    description=scene_data.get('description', candidate['content']),
                    audio_transcript=scene_data.get('transcript', ''),
                    labels=scene_data.get('labels', []),
                    confidence_score=candidate['similarity']
                ),
                relevance_score=candidate['similarity'],
                explanation=explanation,
                start_time=scene_data.get('start_time', 0),
                end_time=scene_data.get('end_time', 30)
            )
            
            results.append(result)
        
        return results
    
    async def _generate_scene_explanation(self, query: str, scene_content: str) -> str:
        """Generate educational explanation for why this scene is relevant"""
        prompt = f"""
        A student asked: "{query}"
        
        This video segment contains: "{scene_content}"
        
        Explain in 1-2 sentences why this segment would help answer their question. Focus on the educational value and what they can learn from it.
        
        Keep it concise and student-friendly.
        """
        
        try:
            explanation = await self.llm_service.generate_response(prompt)
            return explanation.strip()
        except Exception as e:
            print(f"Failed to generate explanation: {str(e)}")
            return "This segment contains relevant educational content for your question."
    
    async def _load_scene_metadata(self, video_id: str, scene_id: str) -> Dict[str, Any]:
        """Load scene metadata from storage"""
        # In production, this would query your database
        # For now, we'll create a mock response
        return {
            'video_title': f'Educational Video {video_id}',
            'start_time': 0,  # Would be loaded from database
            'end_time': 30,   # Would be loaded from database
            'description': 'Educational content',
            'transcript': '',
            'labels': ['educational-content']
        }
    
    async def _generate_suggestions(self, query: str, results: List[SearchResult]) -> List[str]:
        """Generate follow-up question suggestions"""
        if not results:
            return []
        
        # Use the top result to generate related questions
        top_result_content = results[0].scene.description if results else ""
        
        prompt = f"""
        A student searched for: "{query}"
        
        Based on this educational content: "{top_result_content}"
        
        Suggest 3 related follow-up questions they might want to ask to deepen their understanding. 
        Make them specific and educational.
        
        Return as a simple list, one question per line.
        """
        
        try:
            suggestions_response = await self.llm_service.generate_response(prompt)
            suggestions = [s.strip() for s in suggestions_response.split('\n') if s.strip()]
            return suggestions[:3]  # Return max 3 suggestions
        except Exception as e:
            print(f"Failed to generate suggestions: {str(e)}")
            return []
    
    async def find_related_scenes(self, scene_id: str, video_id: str, max_results: int = 5) -> List[SearchResult]:
        """Find scenes related to a given scene"""
        # Load the target scene's embedding
        target_embedding_path = os.path.join(settings.EMBEDDINGS_DIR, video_id, f"{scene_id}.pkl")
        
        if not os.path.exists(target_embedding_path):
            return []
        
        try:
            with open(target_embedding_path, 'rb') as f:
                target_data = pickle.load(f)
            
            target_embedding = target_data['embedding']
            
            # Find similar scenes
            candidates = await self._find_candidate_scenes(target_embedding, video_id, max_results + 1)
            
            # Remove the original scene from results
            candidates = [c for c in candidates if c['scene_id'] != scene_id]
            
            # Convert to SearchResult format
            results = []
            for candidate in candidates[:max_results]:
                scene_data = await self._load_scene_metadata(candidate['video_id'], candidate['scene_id'])
                
                result = SearchResult(
                    scene_id=candidate['scene_id'],
                    video_id=candidate['video_id'],
                    video_title=scene_data.get('video_title', 'Educational Video'),
                    scene=Scene(
                        id=candidate['scene_id'],
                        start_time=scene_data.get('start_time', 0),
                        end_time=scene_data.get('end_time', 30),
                        description=scene_data.get('description', candidate['content']),
                        audio_transcript=scene_data.get('transcript', ''),
                        labels=scene_data.get('labels', []),
                        confidence_score=candidate['similarity']
                    ),
                    relevance_score=candidate['similarity'],
                    explanation="Related educational content",
                    start_time=scene_data.get('start_time', 0),
                    end_time=scene_data.get('end_time', 30)
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Error finding related scenes: {str(e)}")
            return []
