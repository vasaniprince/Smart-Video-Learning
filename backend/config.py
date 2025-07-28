# backend/app/config.py
from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # API Keys
    VIDEODB_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    
    # VideoDB Configuration
    VIDEODB_COLLECTION_ID: str = ""
    
    # Database
    DATABASE_URL: str = "sqlite:///./video_learning.db"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8000", "http://localhost:8501"]
    
    # File Upload
    UPLOAD_DIR: str = "data/videos"
    PROCESSED_DIR: str = "data/processed"
    EMBEDDINGS_DIR: str = "data/embeddings"
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB
    
    # LLM Settings
    LLM_MODEL: str = "gpt-4"
    LLM_TEMPERATURE: float = 0.7
    MAX_TOKENS: int = 1000
    
    # Scene Detection
    SCENE_THRESHOLD: float = 0.3
    MIN_SCENE_LENGTH: int = 10  # seconds
    
    # Search Settings
    TOP_K_RESULTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.7
    
    class Config:
        env_file = ".env"

settings = Settings()