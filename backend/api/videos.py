# backend/api/videos.py
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse,StreamingResponse
from typing import List, Optional
import os
import uuid
from datetime import datetime

from models.video import (
    VideoUploadRequest,
    VideoUploadResponse,
    VideoMetadata,
    VideoStatus,
    VideoWithScenes,
    Scene  # Add Scene import
)
# Use simplified processor for testing (comment out the original)
# from services.video_processor import VideoProcessor

# Create a simple inline processor to avoid import issues
class VideoProcessor:
    def __init__(self):
        pass
        
    async def process_video(self, file_path: str, metadata):
        """
        Simplified video processing for testing (without VideoDB)
        """
        import asyncio
        from models.video import Scene, VideoWithScenes
        
        try:
            # Update status
            metadata.status = VideoStatus.PROCESSING
            
            # Simulate processing time
            await asyncio.sleep(2)
            
            # Mock transcript
            transcript = f"This is a mock transcript for the educational video: {metadata.title}. " \
                        f"It contains educational content about {metadata.subject or 'various topics'}."
            
            # Mock scenes
            mock_scenes = []
            for i in range(5):  # Create 5 mock scenes
                scene = Scene(
                    id=f"scene_{i}",
                    start_time=i * 30,
                    end_time=(i + 1) * 30,
                    description=f"Educational segment {i + 1} covering {metadata.subject or 'general'} concepts",
                    audio_transcript=f"Mock transcript for scene {i + 1}",
                    labels=["educational-content", metadata.subject or "general"],
                    confidence_score=0.8
                )
                mock_scenes.append(scene)
            
            # Mock duration
            metadata.duration = 150.0  # 2.5 minutes
            
            # Update status to indexed
            metadata.status = VideoStatus.INDEXED
            metadata.updated_at = datetime.now()
            
            return VideoWithScenes(
                metadata=metadata,
                scenes=mock_scenes,
                transcript=transcript
            )
            
        except Exception as e:
            metadata.status = VideoStatus.FAILED
            raise Exception(f"Video processing failed: {str(e)}")
from config import settings

router = APIRouter(tags=["videos"], prefix="/api/videos")

# Initialize video processor
video_processor = VideoProcessor()

# In-memory storage for demo (use database in production)
videos_db = {}

@router.post(
    "/upload",
    response_model=VideoUploadResponse,
    summary="Upload a video file",
    description="Upload and process a video file for educational content extraction"
)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="The video file to upload"),
    title: Optional[str] = Form(None, description="Video title"),
    description: Optional[str] = Form(None, description="Video description"),
    subject: Optional[str] = Form(None, description="Subject category"),
    difficulty_level: Optional[str] = Form(None, description="Difficulty level"),
    tags: str = Form("", description="Comma-separated tags")
):
    """
    Upload and process a video file with the following steps:
    
    - Validate file type and size
    - Generate unique ID
    - Save file to storage
    - Create metadata
    - Start background processing
    """
    
    # Validate file
    if not file.content_type or not file.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    try:
        # Read file content to check size
        content = await file.read()
        file_size = len(content)
        
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail=f"File too large. Max size: {settings.MAX_FILE_SIZE/1024/1024:.1f}MB")
    except Exception as e:
        print(f"Error checking file size: {e}")
        # Reset file pointer
        await file.seek(0)
        content = await file.read()
    
    # Generate unique video ID
    video_id = str(uuid.uuid4())
    
    # Create directories
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Save uploaded file
    file_path = os.path.join(settings.UPLOAD_DIR, f"{video_id}_{file.filename}")
    
    try:
        with open(file_path, "wb") as buffer:
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Create video metadata
    metadata = VideoMetadata(
        id=video_id,
        title=title or file.filename,
        description=description,
        duration=0.0,  # Will be updated after processing
        file_path=file_path,
        status=VideoStatus.UPLOADING,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tags=tags.split(',') if tags else [],
        subject=subject,
        difficulty_level=difficulty_level
    )
    
    # Store in database
    videos_db[video_id] = metadata
    
    # Start background processing
    background_tasks.add_task(process_video_background, video_id, file_path, metadata)
    
    return VideoUploadResponse(
        video_id=video_id,
        status="uploaded",
        message="Video uploaded successfully. Processing will begin shortly."
    )

async def process_video_background(video_id: str, file_path: str, metadata: VideoMetadata):
    """Background task to process video"""
    try:
        print(f"Starting video processing for {video_id}")
        
        # Update status to processing
        metadata.status = VideoStatus.PROCESSING
        videos_db[video_id] = metadata
        print(f"Updated status to PROCESSING for {video_id}")
        
        # Process video
        processed_video = await video_processor.process_video(file_path, metadata)
        
        # Update database
        videos_db[video_id] = processed_video.metadata
        
        print(f"Video {video_id} processed successfully with status: {processed_video.metadata.status}")
        
    except Exception as e:
        print(f"Video processing failed for {video_id}: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        
        # Update status to failed
        metadata.status = VideoStatus.FAILED
        metadata.updated_at = datetime.now()
        videos_db[video_id] = metadata
        print(f"Updated status to FAILED for {video_id}")

@router.get("/", response_model=List[VideoMetadata])
async def list_videos(
    subject: Optional[str] = None,
    difficulty: Optional[str] = None,
    status: Optional[VideoStatus] = None
):
    """List all videos with optional filtering"""
    videos = list(videos_db.values())
    
    # Apply filters
    if subject:
        videos = [v for v in videos if v.subject == subject]
    
    if difficulty:
        videos = [v for v in videos if v.difficulty_level == difficulty]
    
    if status:
        videos = [v for v in videos if v.status == status]
    
    # Sort by creation date (newest first)
    videos.sort(key=lambda x: x.created_at, reverse=True)
    
    return videos

@router.get("/{video_id}", response_model=VideoMetadata)
async def get_video(video_id: str):
    """Get video metadata by ID"""
    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return videos_db[video_id]

@router.get("/{video_id}/scenes")
async def get_video_scenes(video_id: str):
    """Get scenes for a specific video"""
    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_metadata = videos_db[video_id]
    
    if video_metadata.status != VideoStatus.INDEXED:
        raise HTTPException(
            status_code=400, 
            detail=f"Video is not ready. Current status: {video_metadata.status}"
        )
    
    # In production, load scenes from database
    # For demo, return mock scenes
    mock_scenes = [
        {
            "id": f"scene_{i}",
            "start_time": i * 30,
            "end_time": (i + 1) * 30,
            "description": f"Educational segment {i + 1}",
            "labels": ["educational-content"],
            "confidence_score": 0.8
        }
        for i in range(5)  # Mock 5 scenes
    ]
    
    return {"video_id": video_id, "scenes": mock_scenes}

@router.delete("/{video_id}")
async def delete_video(video_id: str):
    """Delete a video and its associated data"""
    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_metadata = videos_db[video_id]
    
    try:
        # Delete video file
        if os.path.exists(video_metadata.file_path):
            os.remove(video_metadata.file_path)
        
        # Delete embeddings
        embeddings_dir = os.path.join(settings.EMBEDDINGS_DIR, video_id)
        if os.path.exists(embeddings_dir):
            import shutil
            shutil.rmtree(embeddings_dir)
        
        # Remove from database
        del videos_db[video_id]
        
        return {"message": "Video deleted successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete video: {str(e)}")

@router.get("/{video_id}/status")
async def get_video_status(video_id: str):
    """Get processing status of a video"""
    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_metadata = videos_db[video_id]
    
    return {
        "video_id": video_id,
        "status": video_metadata.status,
        "created_at": video_metadata.created_at,
        "updated_at": video_metadata.updated_at
    }

@router.get("/{video_id}/play/{scene_id}")
async def get_playback_info(video_id: str, scene_id: str):
    """Get video playback information for a scene"""
    if video_id not in videos_db:
        raise HTTPException(status_code=404, detail="Video not found")
    
    video_metadata = videos_db[video_id]
    
    # Mock scene data - replace with actual scene loading
    scene_data = {
        "start_time": 0,
        "end_time": 30,
        "description": "Educational content"
    }
    
    return {
        "success": True,
        "video_id": video_id,
        "scene_id": scene_id,
        "video_file": video_metadata.file_path,
        "video_url": f"/api/videos/{video_id}/stream",
        "start_time": scene_data["start_time"],
        "end_time": scene_data["end_time"],
        "title": video_metadata.title
    }