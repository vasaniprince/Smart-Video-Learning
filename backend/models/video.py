# backend/models/video.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class VideoStatus(str, Enum):
    """Video processing status"""
    UPLOADING = "uploading"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"

class Scene(BaseModel):
    """Video scene information"""
    id: str = Field(..., description="Unique scene identifier")
    start_time: float = Field(..., description="Scene start time in seconds")
    end_time: float = Field(..., description="Scene end time in seconds")
    description: str = Field(..., description="Scene description")
    visual_features: Optional[Dict[str, Any]] = Field(None, description="Visual features detected in the scene")
    audio_transcript: Optional[str] = Field(None, description="Scene transcript")
    labels: List[str] = Field(default=[], description="Scene labels/tags")
    confidence_score: float = Field(default=0.0, description="Confidence score of scene detection")

class VideoMetadata(BaseModel):
    """Video metadata information"""
    id: str = Field(..., description="Unique video identifier")
    title: str = Field(..., description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    duration: float = Field(..., description="Video duration in seconds")
    file_path: str = Field(..., description="Path to video file")
    videodb_id: Optional[str] = Field(None, description="VideoDB identifier")
    status: VideoStatus = Field(default=VideoStatus.UPLOADING, description="Processing status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    tags: List[str] = Field(default=[], description="Video tags")
    subject: Optional[str] = Field(None, description="Subject category")
    difficulty_level: Optional[str] = Field(None, description="Difficulty level")

    class Config:
        schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Introduction to Python",
                "description": "Basic Python programming concepts",
                "duration": 300.0,
                "file_path": "/data/videos/intro_python.mp4",
                "status": "indexed",
                "created_at": "2024-03-20T10:00:00",
                "updated_at": "2024-03-20T10:05:00",
                "tags": ["python", "programming", "beginner"],
                "subject": "Programming",
                "difficulty_level": "Beginner"
            }
        }

class VideoWithScenes(BaseModel):
    """Video with its scenes"""
    metadata: VideoMetadata
    scenes: List[Scene] = Field(default=[], description="List of scenes in the video")
    transcript: Optional[str] = Field(None, description="Full video transcript")

class VideoUploadRequest(BaseModel):
    """Video upload request parameters"""
    title: str = Field(..., description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    subject: Optional[str] = Field(None, description="Subject category")
    difficulty_level: Optional[str] = Field(None, description="Difficulty level")
    tags: List[str] = Field(default=[], description="Video tags")

class VideoUploadResponse(BaseModel):
    """Video upload response"""
    video_id: str = Field(..., description="Unique video identifier")
    status: str = Field(..., description="Upload status")
    message: str = Field(..., description="Status message")

    class Config:
        schema_extra = {
            "example": {
                "video_id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "uploaded",
                "message": "Video uploaded successfully. Processing will begin shortly."
            }
        }