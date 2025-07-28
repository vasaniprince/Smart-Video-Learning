# backend/models/query.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class SearchQuery(BaseModel):
    query: str
    video_id: Optional[str] = None
    subject_filter: Optional[str] = None
    difficulty_filter: Optional[str] = None
    max_results: int = 5
    min_confidence: float = 0.5

class SearchResult(BaseModel):
    scene_id: str
    video_id: str
    video_title: str
    relevance_score: float
    explanation: Optional[str] = None
    start_time: float
    end_time: float

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_results: int
    processing_time: float
    suggestions: List[str] = []

class UserFeedback(BaseModel):
    """User feedback for search results"""
    query: str = Field(..., description="The search query that was used")
    scene_id: str = Field(..., description="ID of the scene that received feedback")
    video_id: str = Field(..., description="ID of the video containing the scene")
    helpful: bool = Field(..., description="Whether the result was helpful")
    feedback_text: Optional[str] = Field(None, description="Optional detailed feedback")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the feedback was submitted")

    class Config:
        schema_extra = {
            "example": {
                "query": "How to solve quadratic equations",
                "scene_id": "scene_123",
                "video_id": "video_456",
                "helpful": True,
                "feedback_text": "This explanation was very clear and helpful",
                "timestamp": "2024-03-20T10:00:00"
            }
        }