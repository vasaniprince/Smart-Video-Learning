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
        
        results = await search_service.search(query)
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
            video_ids=video_ids,
            subject_filters=subjects,
            difficulty_filters=difficulty,
            scene_types=scene_types,
            max_results=max_results,
            include_context=include_context
        )
        
        results = await search_service.search(query)
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/feedback")
async def submit_feedback(feedback: UserFeedback):
    """Submit feedback on search results"""
    try:
        # In a real implementation, this would store feedback in a database
        # For now, just log it
        print(f"Received feedback: {feedback.dict()}")
        
        return {"message": "Feedback received successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit feedback: {str(e)}")

@router.get("/stats")
async def get_search_stats():
    """Get statistics about the video index"""
    try:
        stats = await search_service.get_video_stats()
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
        # Simple implementation - in practice, you'd use more sophisticated methods
        suggestions = []
        
        # Extract common educational terms from indexed content
        common_terms = set()
        for video in search_service.video_index.values():
            if video.transcript:
                words = video.transcript.lower().split()
                common_terms.update([w for w in words if len(w) > 4])
        
        # Find terms that start with or contain the query
        query_lower = query.lower()
        matching_terms = [
            term for term in common_terms 
            if query_lower in term and len(term) > len(query)
        ]
        
        # Simple ranking by length (shorter terms first)
        matching_terms.sort(key=len)
        suggestions = matching_terms[:limit]
        
        return {"query": query, "suggestions": suggestions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")