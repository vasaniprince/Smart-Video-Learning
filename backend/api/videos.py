# backend/api/videos.py
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse
from typing import List, Optional
import os
import uuid
from datetime import datetime

from models.video import (
    VideoUploadRequest,
    VideoUploadResponse,
    VideoMetadata,
    VideoStatus,
    VideoWithScenes
)
from services.video_processor import VideoProcessor
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
    description="Upload and process a video file for educational content extraction",
    tags=["videos"],
    operation_id="upload_video"
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
    if not file.content_type.startswith('video/'):
        raise HTTPException(status_code=400, detail="File must be a video")
    
    try:
        file_size = os.fstat(file.file.fileno()).st_size
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
    except Exception as e:
        print(f"Error checking file size: {e}")
        # Continue if we can't check size
        pass
    
    # Generate unique video ID
    video_id = str(uuid.uuid4())
    
    # Create directories
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Save uploaded file
    file_path = os.path.join(settings.UPLOAD_DIR, f"{video_id}_{file.filename}")
    
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
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
        # Process video
        processed_video = await video_processor.process_video(file_path, metadata)
        
        # Update database
        videos_db[video_id] = processed_video.metadata
        
        print(f"Video {video_id} processed successfully")
        
    except Exception as e:
        # Update status to failed
        metadata.status = VideoStatus.FAILED
        videos_db[video_id] = metadata
        print(f"Video processing failed for {video_id}: {str(e)}")

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

# backend/app/api/search.py
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import asyncio

from models.query import SearchQuery, SearchResponse, SearchResult
from services.semantic_search import SemanticSearchService
from services.llm_service import LLMService

router = APIRouter()
search_service = SemanticSearchService()
llm_service = LLMService()

@router.post("/", response_model=SearchResponse)
async def search_scenes(query: SearchQuery):
    """Search for educational video scenes based on natural language query"""
    
    try:
        # Perform semantic search
        results = await search_service.search_scenes(query)
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/suggest")
async def get_search_suggestions(
    q: str = Query(..., description="Partial query for suggestions"),
    limit: int = Query(5, description="Maximum number of suggestions")
):
    """Get search suggestions based on partial query"""
    
    try:
        # Generate suggestions using LLM
        prompt = f"""
        A student is typing a search query: "{q}"
        
        Suggest {limit} complete educational questions they might be trying to ask.
        Focus on common learning needs and make them specific and helpful.
        
        Return as a simple list, one suggestion per line.
        """
        
        suggestions_response = await llm_service.generate_response(prompt)
        suggestions = [s.strip() for s in suggestions_response.split('\n') if s.strip()]
        
        return {"query": q, "suggestions": suggestions[:limit]}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Suggestion generation failed: {str(e)}")

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

@router.post("/analyze-intent")
async def analyze_query_intent(query: str):
    """Analyze the learning intent behind a search query"""
    
    try:
        intent_analysis = await llm_service.classify_question_intent(query)
        
        return {
            "query": query,
            "analysis": intent_analysis
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Intent analysis failed: {str(e)}")

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
    
    # In production, query database for unique subjects
    from api.videos import videos_db
    
    subjects = set()
    for video in videos_db.values():
        if video.subject:
            subjects.add(video.subject)
    
    return {"subjects": sorted(list(subjects))}

@router.post("/feedback")
async def submit_search_feedback(
    query: str,
    scene_id: str,
    video_id: str,
    helpful: bool,
    feedback_text: Optional[str] = None
):
    """Submit feedback on search results for improvement"""
    
    # In production, store this feedback for model improvement
    feedback_data = {
        "query": query,
        "scene_id": scene_id,
        "video_id": video_id,
        "helpful": helpful,
        "feedback_text": feedback_text,
        "timestamp": datetime.now()
    }
    
    # For demo, just log it
    print(f"Search feedback received: {feedback_data}")
    
    return {"message": "Feedback received successfully"}

from datetime import datetime