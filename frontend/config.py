import os

class Config:
    API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:8000')
    
    # Streamlit settings
    PAGE_TITLE = "Video Learning Assistant"
    PAGE_ICON = "🎓"
    LAYOUT = "wide"
    
    # Upload settings
    MAX_FILE_SIZE_MB = 500
    SUPPORTED_VIDEO_FORMATS = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv']
    
    # UI settings
    RESULTS_PER_PAGE = 10
    AUTO_REFRESH_INTERVAL = 30  # seconds