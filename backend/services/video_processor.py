# backend/app/services/video_processor.py
import os
import asyncio
from typing import List, Dict, Any, Optional
from videodb import connect, _upload
import uuid
from datetime import datetime

from config import settings
from models.video import VideoMetadata, VideoStatus, Scene, VideoWithScenes
from services.scene_detector import SceneDetector
from services.llm_service import LLMService
from utils.embeddings import EmbeddingGenerator

class VideoProcessor:
    def __init__(self):
        self.videodb_conn = connect(api_key=settings.VIDEODB_API_KEY)
        self.scene_detector = SceneDetector()
        self.llm_service = LLMService()
        self.embedding_generator = EmbeddingGenerator()
        
    async def process_video(self, file_path: str, metadata: VideoMetadata) -> VideoWithScenes:
        """
        Main video processing pipeline:
        1. Upload to VideoDB
        2. Extract transcript and scenes
        3. Generate semantic embeddings
        4. Create educational labels
        """
        try:
            # Update status
            metadata.status = VideoStatus.PROCESSING
            
            # Step 1: Upload to VideoDB
            videodb_video = await self._upload_to_videodb(file_path)
            metadata.videodb_id = videodb_video.id
            
            # Step 2: Get transcript from VideoDB
            transcript = await self._extract_transcript(videodb_video)
            
            # Step 3: Detect scenes using VideoDB scene detection
            raw_scenes = await self._detect_scenes(videodb_video)
            
            # Step 4: Enhance scenes with AI analysis
            enhanced_scenes = await self._enhance_scenes(raw_scenes, transcript)
            
            # Step 5: Generate embeddings for search
            await self._generate_embeddings(enhanced_scenes, metadata.id)
            
            # Update status
            metadata.status = VideoStatus.INDEXED
            metadata.updated_at = datetime.now()
            
            return VideoWithScenes(
                metadata=metadata,
                scenes=enhanced_scenes,
                transcript=transcript
            )
            
        except Exception as e:
            metadata.status = VideoStatus.FAILED
            raise Exception(f"Video processing failed: {str(e)}")
    
    async def _upload_to_videodb(self, file_path: str):
        """Upload video to VideoDB"""
        try:
            video = _upload(
                file_path=file_path,
                collection_id=settings.VIDEODB_COLLECTION_ID
            )
            return video
        except Exception as e:
            raise Exception(f"VideoDB upload failed: {str(e)}")
    
    async def _extract_transcript(self, videodb_video) -> str:
        """Extract transcript using VideoDB speech-to-text"""
        try:
            # Use VideoDB's built-in speech recognition
            transcript_result = videodb_video.generate_transcript()
            return transcript_result.text if transcript_result else ""
        except Exception as e:
            print(f"Transcript extraction failed: {str(e)}")
            return ""
    
    async def _detect_scenes(self, videodb_video) -> List[Dict[str, Any]]:
        """Detect scenes using VideoDB scene detection"""
        try:
            # Use VideoDB's scene detection
            scenes = videodb_video.get_scenes(
                threshold=settings.SCENE_THRESHOLD
            )
            
            raw_scenes = []
            for i, scene in enumerate(scenes):
                raw_scenes.append({
                    'id': f"scene_{i}",
                    'start_time': scene.start,
                    'end_time': scene.end,
                    'thumbnail_url': scene.thumbnail_url if hasattr(scene, 'thumbnail_url') else None
                })
            
            return raw_scenes
            
        except Exception as e:
            print(f"Scene detection failed: {str(e)}")
            # Fallback: create scenes every 30 seconds
            duration = videodb_video.length
            scenes = []
            for i in range(0, int(duration), 30):
                scenes.append({
                    'id': f"scene_{i//30}",
                    'start_time': i,
                    'end_time': min(i + 30, duration)
                })
            return scenes
    
    async def _enhance_scenes(self, raw_scenes: List[Dict[str, Any]], transcript: str) -> List[Scene]:
        """Enhance scenes with AI-generated descriptions and labels"""
        enhanced_scenes = []
        
        for raw_scene in raw_scenes:
            # Extract transcript segment for this scene
            scene_transcript = self._extract_transcript_segment(
                transcript, 
                raw_scene['start_time'], 
                raw_scene['end_time']
            )
            
            # Generate AI description and labels
            description, labels = await self._generate_scene_metadata(scene_transcript)
            
            # Create enhanced scene
            scene = Scene(
                id=raw_scene['id'],
                start_time=raw_scene['start_time'],
                end_time=raw_scene['end_time'],
                description=description,
                audio_transcript=scene_transcript,
                labels=labels,
                confidence_score=0.8  # Default confidence
            )
            
            enhanced_scenes.append(scene)
        
        return enhanced_scenes
    
    def _extract_transcript_segment(self, transcript: str, start_time: float, end_time: float) -> str:
        """Extract transcript segment for given time range"""
        # This is a simplified version - you might want to use more sophisticated
        # timestamp-based extraction if VideoDB provides word-level timestamps
        words = transcript.split()
        # Rough estimation: assume 2 words per second average speaking rate
        words_per_second = 2
        start_word = int(start_time * words_per_second)
        end_word = int(end_time * words_per_second)
        
        return " ".join(words[start_word:end_word])
    
    async def _generate_scene_metadata(self, scene_transcript: str) -> tuple[str, List[str]]:
        """Generate description and educational labels for scene"""
        if not scene_transcript.strip():
            return "Scene with no audio content", ["visual-content"]
        
        prompt = f"""
        Analyze this educational video segment transcript and provide:
        1. A concise description (1-2 sentences) of what's being taught/demonstrated
        2. Educational labels/tags that categorize the content type
        
        Transcript: "{scene_transcript}"
        
        Focus on identifying:
        - Concept explanations
        - Demonstrations/experiments
        - Problem-solving steps  
        - Definitions
        - Examples
        - Visual aids/diagrams
        
        Return as JSON: {{"description": "...", "labels": ["label1", "label2", ...]}}
        """
        
        try:
            result = await self.llm_service.generate_response(prompt)
            import json
            parsed = json.loads(result)
            return parsed.get("description", "Educational content"), parsed.get("labels", [])
        except Exception as e:
            print(f"AI enhancement failed: {str(e)}")
            return f"Educational segment: {scene_transcript[:100]}...", ["general-content"]
    
    async def _generate_embeddings(self, scenes: List[Scene], video_id: str):
        """Generate embeddings for semantic search"""
        for scene in scenes:
            # Combine description and transcript for embedding
            content = f"{scene.description} {scene.audio_transcript or ''}"
            embedding = await self.embedding_generator.generate_embedding(content)
            
            # Store embedding (you might want to use a vector database here)
            await self._store_embedding(video_id, scene.id, embedding, content)
    
    async def _store_embedding(self, video_id: str, scene_id: str, embedding: List[float], content: str):
        """Store embedding in vector database"""
        # Implementation would depend on your chosen vector database
        # For now, we'll save to file system
        import pickle
        import os
        
        embeddings_dir = os.path.join(settings.EMBEDDINGS_DIR, video_id)
        os.makedirs(embeddings_dir, exist_ok=True)
        
        embedding_data = {
            'scene_id': scene_id,
            'embedding': embedding,
            'content': content
        }
        
        with open(os.path.join(embeddings_dir, f"{scene_id}.pkl"), 'wb') as f:
            pickle.dump(embedding_data, f)