# backend/api/search.py
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from models.query import SearchQuery, SearchResponse, UserFeedback
from services.semantic_search import SemanticSearchService
from services.llm_service import LLMService

router = APIRouter(tags=["search"], prefix="/api/search")

# Initialize search service
search_service = SemanticSearchService()


@router.post("/feedback")
async def submit_feedback(feedback: UserFeedback):
    """Submit feedback on search results for improvement"""
    try:
        # In production, store this feedback in a database
        # For demo, just log it
        print(f"Search feedback received: {feedback.dict()}")
        return {"message": "Feedback received successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")



@router.post("/", response_model=SearchResponse)
async def search_videos(query: SearchQuery):
    """Search for video segments using natural language"""
    try:
        if not query.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        results = await search_service.search_scenes(query)
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/", response_model=SearchResponse)
async def search_videos_get(
    q: str = Query(..., description="Search query"),
    video_ids: Optional[List[str]] = Query(None, description="Filter by video IDs"),
    subjects: Optional[List[str]] = Query(None, description="Filter by subjects"),
    difficulty: Optional[List[str]] = Query(None, description="Filter by difficulty"),
    scene_types: Optional[List[str]] = Query(None, description="Filter by scene types"),
    max_results: int = Query(10, description="Maximum results", ge=1, le=50),
    include_context: bool = Query(True, description="Include AI-generated context")
):
    """Search for video segments using GET method"""
    try:
        query = SearchQuery(
            query=q,
            max_results=max_results
        )
        
        results = await search_service.search_scenes(query)
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/stats")
async def get_search_stats():
    """Get statistics about the video index"""
    try:
        # Import videos_db from videos module
        from api.videos import videos_db
        
        total_videos = len(videos_db)
        indexed_videos = len([v for v in videos_db.values() if v.status == "indexed"])
        subjects = list(set(v.subject for v in videos_db.values() if v.subject))
        
        stats = {
            "total_videos": total_videos,
            "indexed_videos": indexed_videos,
            "processing_videos": total_videos - indexed_videos,
            "available_subjects": subjects,
            "total_subjects": len(subjects)
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.get("/suggestions")
async def get_search_suggestions(
    query: str = Query(..., description="Partial query for suggestions"),
    limit: int = Query(5, description="Maximum suggestions", ge=1, le=20)
):
    """Get search suggestions based on partial query"""
    try:
        # Initialize LLM service for generating suggestions
        llm_service = LLMService()
        
        # Generate suggestions using LLM
        prompt = f"""
        A student is typing a search query: "{query}"
        
        Based on common educational topics and learning needs, suggest {limit} complete questions they might be trying to ask.
        Focus on:
        - Common educational subjects (math, science, history, programming, etc.)
        - Typical learning questions (how to, what is, explain, demonstrate, etc.)
        - Making suggestions specific and helpful for learning
        
        Return as a simple list, one suggestion per line.
        Do not include numbers or bullets, just the suggestions.
        """
        
        suggestions_response = await llm_service.generate_response(prompt)
        suggestions = [s.strip() for s in suggestions_response.split('\n') if s.strip() and len(s.strip()) > 5]
        
        # Fallback suggestions if LLM fails
        if not suggestions:
            fallback_suggestions = [
                f"What is {query}?",
                f"How does {query} work?",
                f"Can you explain {query}?",
                f"Show me examples of {query}",
                f"What are the basics of {query}?"
            ]
            suggestions = fallback_suggestions[:limit]
        
        return {"query": query, "suggestions": suggestions[:limit]}
        
    except Exception as e:
        print(f"Suggestion generation error: {str(e)}")
        # Return fallback suggestions on error
        fallback_suggestions = [
            f"What is {query}?",
            f"How does {query} work?",
            f"Can you explain {query}?"
        ]
        return {"query": query, "suggestions": fallback_suggestions[:limit]}

@router.get("/topics")
async def get_popular_topics():
    """Get popular search topics and subjects"""
    
    # In production, this would analyze actual search data
    popular_topics = [
        {"topic": "Physics Demonstrations", "count": 45, "category": "science"},
        {"topic": "Mathematical Problem Solving", "count": 38, "category": "mathematics"},
        {"topic": "Chemistry Experiments", "count": 32, "category": "science"},
        {"topic": "Programming Tutorials", "count": 29, "category": "technology"},
        {"topic": "Historical Analysis", "count": 25, "category": "humanities"},
        {"topic": "Language Learning", "count": 22, "category": "language"},
        {"topic": "Art Techniques", "count": 18, "category": "arts"},
        {"topic": "Biology Concepts", "count": 16, "category": "science"}
    ]
    
    return {"popular_topics": popular_topics}

@router.get("/subjects")
async def get_available_subjects():
    """Get list of available subjects from processed videos"""
    
    try:
        # Import videos_db from videos module
        from api.videos import videos_db
        
        subjects = set()
        for video in videos_db.values():
            if video.subject:
                subjects.add(video.subject)
        
        return {"subjects": sorted(list(subjects))}
    except Exception as e:
        # Return default subjects if no videos exist yet
        default_subjects = ["Science", "Mathematics", "Programming", "History", "Language Arts", "Arts"]
        return {"subjects": default_subjects}

@router.post("/analyze-intent")
async def analyze_query_intent(query: str):
    """Analyze the learning intent behind a search query"""
    
    try:
        llm_service = LLMService()
        intent_analysis = await llm_service.classify_question_intent(query)
        
        return {
            "query": query,
            "analysis": intent_analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intent analysis failed: {str(e)}")

@router.get("/related/{video_id}/{scene_id}")
async def get_related_scenes(
    video_id: str,
    scene_id: str,
    limit: int = Query(5, description="Maximum number of related scenes")
):
    """Get scenes related to a specific scene"""
    
    try:
        related_scenes = await search_service.find_related_scenes(scene_id, video_id, limit)
        
        return {
            "source_scene": {"video_id": video_id, "scene_id": scene_id},
            "related_scenes": related_scenes,
            "total_found": len(related_scenes)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Related scenes search failed: {str(e)}")