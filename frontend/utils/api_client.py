import requests
import streamlit as st
from typing import Dict, Any, List, Optional
import json

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            
            if response.content:
                return response.json()
            return {"success": True}
            
        except requests.exceptions.RequestException as e:
            st.error(f"API request failed: {str(e)}")
            return None
        except json.JSONDecodeError:
            st.error("Invalid response format from server")
            return None
    
    # Video operations
    def upload_video(self, file, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Upload video file with metadata"""
        files = {'file': (file.name, file.getvalue(), file.type)}
        data = {
            'title': metadata.get('title', ''),
            'description': metadata.get('description', ''),
            'subject': metadata.get('subject', ''),
            'difficulty_level': metadata.get('difficulty_level', ''),
            'tags': metadata.get('tags', '')
        }
        
        return self._make_request('POST', '/api/videos/upload', files=files, data=data)
    
    def get_videos(self) -> List[Dict[str, Any]]:
        """Get list of videos"""
        result = self._make_request('GET', '/api/videos/')
        return result if result else []
    
    def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video by ID"""
        return self._make_request('GET', f'/api/videos/{video_id}')
    
    def get_video_scenes(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get scenes for a video"""
        return self._make_request('GET', f'/api/videos/{video_id}/scenes')
    
    def get_video_status(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video processing status"""
        return self._make_request('GET', f'/api/videos/{video_id}/status')
    
    def delete_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Delete video"""
        return self._make_request('DELETE', f'/api/videos/{video_id}')
    
    # Search operations
    def search_scenes(self, query_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Search for scenes"""
        # Convert frontend query params to backend SearchQuery format
        search_query = {
            "query": query_params.get("query", ""),
            "max_results": query_params.get("max_results", 5),
            "min_confidence": query_params.get("min_confidence", 0.5),
            "video_id": query_params.get("video_id"),
            "subject_filter": query_params.get("subject_filter"),
            "difficulty_filter": query_params.get("difficulty_filter")
        }
        return self._make_request('POST', '/api/search/', json=search_query)
    
    def get_search_suggestions(self, query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
        """Get search suggestions"""
        params = {'q': query, 'limit': limit}
        return self._make_request('GET', '/api/search/suggest', params=params)
    
    def get_related_scenes(self, video_id: str, scene_id: str, limit: int = 5) -> Optional[Dict[str, Any]]:
        """Get related scenes"""
        params = {'limit': limit}
        return self._make_request('GET', f'/api/search/related/{video_id}/{scene_id}', params=params)
    
    def submit_feedback(self, feedback_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Submit search feedback"""
        # Backend expects individual parameters, not nested json
        params = {
            'query': feedback_data.get('query', ''),
            'scene_id': feedback_data.get('scene_id', ''),
            'video_id': feedback_data.get('video_id', ''),
            'helpful': feedback_data.get('helpful', False),
            'feedback_text': feedback_data.get('feedback_text')
        }
        return self._make_request('POST', '/api/search/feedback', params=params)
    
    def get_popular_topics(self) -> Optional[Dict[str, Any]]:
        """Get popular search topics"""
        return self._make_request('GET', '/api/search/topics')
    
    def analyze_query_intent(self, query: str) -> Optional[Dict[str, Any]]:
        """Analyze search query intent"""
        params = {'query': query}
        return self._make_request('POST', '/api/search/analyze-intent', params=params)