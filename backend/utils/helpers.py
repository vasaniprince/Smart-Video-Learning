import os
import shutil
import hashlib
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
import pickle

def ensure_directory(path: str):
    """Ensure directory exists, create if it doesn't"""
    os.makedirs(path, exist_ok=True)

def get_file_hash(file_path: str) -> str:
    """Generate MD5 hash of file for deduplication"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable format"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes:02d}:{seconds:02d}"

def format_timestamp(seconds: float) -> str:
    """Format timestamp for video player (MM:SS or HH:MM:SS)"""
    return format_duration(seconds)

def parse_timestamp(timestamp_str: str) -> float:
    """Parse timestamp string to seconds"""
    try:
        parts = timestamp_str.split(':')
        if len(parts) == 2:  # MM:SS
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        else:
            return float(timestamp_str)
    except ValueError:
        return 0.0

def clean_text(text: str) -> str:
    """Clean text for processing"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove common filler words for better search
    filler_words = ['um', 'uh', 'er', 'ah', 'like', 'you know']
    words = text.split()
    cleaned_words = [word for word in words if word.lower() not in filler_words]
    
    return ' '.join(cleaned_words)

def extract_keywords(text: str, min_length: int = 3) -> List[str]:
    """Extract meaningful keywords from text"""
    import re
    
    # Remove punctuation and convert to lowercase
    text = re.sub(r'[^\w\s]', '', text.lower())
    words = text.split()
    
    # Filter by length and remove common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are',
        'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do',
        'does', 'did', 'will', 'would', 'should', 'could', 'can', 'may',
        'might', 'must', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
        'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
    }
    
    keywords = [
        word for word in words 
        if len(word) >= min_length and word not in stop_words
    ]
    
    return list(set(keywords))  # Remove duplicates

def save_json(data: Dict[str, Any], file_path: str):
    """Save data to JSON file"""
    ensure_directory(os.path.dirname(file_path))
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)

def load_json(file_path: str) -> Optional[Dict[str, Any]]:
    """Load data from JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def save_pickle(data: Any, file_path: str):
    """Save data to pickle file"""
    ensure_directory(os.path.dirname(file_path))
    with open(file_path, 'wb') as f:
        pickle.dump(data, f)

def load_pickle(file_path: str) -> Optional[Any]:
    """Load data from pickle file"""
    try:
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    except (FileNotFoundError, pickle.PickleError):
        return None

def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB"""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except OSError:
        return 0.0

def is_video_file(filename: str) -> bool:
    """Check if file is a supported video format"""
    video_extensions = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v'}
    return os.path.splitext(filename.lower())[1] in video_extensions

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    import re
    # Remove/replace unsafe characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove extra spaces and dots
    sanitized = re.sub(r'\.+', '.', sanitized)
    sanitized = re.sub(r'\s+', '_', sanitized)
    return sanitized.strip('.')

class ProgressTracker:
    """Track progress of long-running operations"""
    
    def __init__(self, total_steps: int, description: str = "Processing"):
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.start_time = datetime.now()
        self.step_times = []
    
    def update(self, step_description: str = ""):
        """Update progress to next step"""
        self.current_step += 1
        current_time = datetime.now()
        self.step_times.append(current_time)
        
        progress = (self.current_step / self.total_steps) * 100
        elapsed = current_time - self.start_time
        
        if self.current_step > 1:
            avg_step_time = elapsed / (self.current_step - 1)
            remaining_steps = self.total_steps - self.current_step
            eta = avg_step_time * remaining_steps
        else:
            eta = timedelta(0)
        
        print(f"{self.description}: {progress:.1f}% ({self.current_step}/{self.total_steps}) - {step_description}")
        if eta.total_seconds() > 0:
            print(f"ETA: {eta}")
    
    def complete(self):
        """Mark progress as complete"""
        total_time = datetime.now() - self.start_time
        print(f"{self.description} completed in {total_time}")

def batch_process(items: List[Any], batch_size: int = 10):
    """Split items into batches for processing"""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]

async def async_batch_process(items: List[Any], async_func, batch_size: int = 5, delay: float = 0.1):
    """Process items in async batches with rate limiting"""
    results = []
    
    for batch in batch_process(items, batch_size):
        batch_tasks = [async_func(item) for item in batch]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
        results.extend(batch_results)
        
        # Rate limiting delay
        if delay > 0:
            await asyncio.sleep(delay)
    
    return results

def calculate_similarity_threshold(similarities: List[float], percentile: float = 75) -> float:
    """Calculate dynamic similarity threshold based on score distribution"""
    if not similarities:
        return 0.5
    
    similarities = sorted(similarities, reverse=True)
    threshold_index = int(len(similarities) * (percentile / 100))
    
    if threshold_index >= len(similarities):
        threshold_index = len(similarities) - 1
    
    return max(similarities[threshold_index], 0.3)  # Minimum threshold of 0.3

def merge_overlapping_segments(segments: List[Tuple[float, float]], max_gap: float = 5.0) -> List[Tuple[float, float]]:
    """Merge overlapping or closely spaced time segments"""
    if not segments:
        return []
    
    # Sort by start time
    segments = sorted(segments, key=lambda x: x[0])
    merged = [segments[0]]
    
    for current_start, current_end in segments[1:]:
        last_start, last_end = merged[-1]
        
        # Check if segments overlap or are close enough to merge
        if current_start <= last_end + max_gap:
            # Merge segments
            merged[-1] = (last_start, max(last_end, current_end))
        else:
            # Add as new segment
            merged.append((current_start, current_end))
    
    return merged

def validate_time_range(start_time: float, end_time: float, max_duration: float) -> Tuple[float, float]:
    """Validate and correct time range"""
    start_time = max(0, start_time)
    end_time = min(max_duration, end_time)
    
    if start_time >= end_time:
        # Ensure minimum segment length of 1 second
        if start_time + 1 <= max_duration:
            end_time = start_time + 1
        else:
            start_time = max(0, end_time - 1)
    
    return start_time, end_time

class CacheManager:
    """Simple file-based cache manager"""
    
    def __init__(self, cache_dir: str, max_age_hours: int = 24):
        self.cache_dir = cache_dir
        self.max_age = timedelta(hours=max_age_hours)
        ensure_directory(cache_dir)
    
    def _get_cache_path(self, key: str) -> str:
        """Get cache file path for key"""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.cache")
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached data"""
        cache_path = self._get_cache_path(key)
        
        if not os.path.exists(cache_path):
            return None
        
        # Check if cache is still valid
        cache_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        if datetime.now() - cache_time > self.max_age:
            os.remove(cache_path)
            return None
        
        return load_pickle(cache_path)
    
    def set(self, key: str, data: Any):
        """Set cached data"""
        cache_path = self._get_cache_path(key)
        save_pickle(data, cache_path)
    
    def clear(self):
        """Clear all cached data"""
        for file in os.listdir(self.cache_dir):
            if file.endswith('.cache'):
                os.remove(os.path.join(self.cache_dir, file))

import os