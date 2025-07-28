# backend/app/services/scene_detector.py
from typing import List, Dict, Any, Tuple
import numpy as np
from config import settings

class SceneDetector:
    """
    Scene detection service that works with VideoDB
    Provides additional scene analysis and filtering capabilities
    """
    
    def __init__(self):
        self.min_scene_length = settings.MIN_SCENE_LENGTH
        self.scene_threshold = settings.SCENE_THRESHOLD
    
    def filter_scenes(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter scenes based on minimum length and merge very short scenes"""
        filtered_scenes = []
        
        for scene in scenes:
            duration = scene['end_time'] - scene['start_time']
            
            # Skip very short scenes
            if duration < self.min_scene_length:
                # Try to merge with previous scene if it exists
                if filtered_scenes:
                    filtered_scenes[-1]['end_time'] = scene['end_time']
                continue
            
            filtered_scenes.append(scene)
        
        return filtered_scenes
    
    def detect_educational_segments(self, scenes: List[Dict[str, Any]], transcript: str) -> List[Dict[str, Any]]:
        """
        Detect educational segments within scenes based on content analysis
        """
        educational_scenes = []
        
        for scene in scenes:
            # Extract transcript for this scene
            scene_transcript = self._extract_scene_transcript(
                transcript, scene['start_time'], scene['end_time']
            )
            
            # Analyze educational content
            education_score = self._calculate_education_score(scene_transcript)
            scene['education_score'] = education_score
            
            # Detect content type
            content_type = self._detect_content_type(scene_transcript)
            scene['content_type'] = content_type
            
            # Only include scenes with sufficient educational content
            if education_score > 0.3:
                educational_scenes.append(scene)
        
        return educational_scenes
    
    def _extract_scene_transcript(self, full_transcript: str, start_time: float, end_time: float) -> str:
        """Extract transcript segment for scene time range"""
        # Simplified extraction - in production, use word-level timestamps
        words = full_transcript.split()
        words_per_second = 2.5  # Average speaking rate
        
        start_word = int(start_time * words_per_second)
        end_word = int(end_time * words_per_second)
        
        return " ".join(words[start_word:end_word])
    
    def _calculate_education_score(self, transcript: str) -> float:
        """Calculate how educational/instructional the content is"""
        if not transcript:
            return 0.0
        
        # Educational indicators
        educational_keywords = [
            'explain', 'demonstrate', 'show', 'example', 'step', 'process',
            'method', 'technique', 'principle', 'concept', 'theory', 'formula',
            'equation', 'definition', 'meaning', 'understand', 'learn', 'study',
            'observe', 'notice', 'important', 'remember', 'key', 'main',
            'first', 'second', 'next', 'then', 'finally', 'because', 'therefore',
            'result', 'conclusion', 'summary', 'review'
        ]
        
        question_indicators = ['what', 'how', 'why', 'when', 'where', 'which']
        
        transcript_lower = transcript.lower()
        words = transcript_lower.split()
        
        if len(words) == 0:
            return 0.0
        
        # Count educational keywords
        edu_count = sum(1 for word in educational_keywords if word in transcript_lower)
        question_count = sum(1 for word in question_indicators if word in transcript_lower)
        
        # Calculate score
        edu_score = edu_count / len(words)
        question_score = question_count / len(words)
        
        # Combine scores
        total_score = (edu_score * 0.7) + (question_score * 0.3)
        
        return min(total_score * 10, 1.0)  # Normalize to 0-1
    
    def _detect_content_type(self, transcript: str) -> str:
        """Detect the type of educational content"""
        if not transcript:
            return "visual-content"
        
        transcript_lower = transcript.lower()
        
        # Content type indicators
        content_patterns = {
            "definition": ["define", "definition", "means", "is defined as", "refers to"],
            "demonstration": ["demonstrate", "show you", "watch", "observe", "see here"],
            "explanation": ["explain", "because", "reason", "why", "how it works"],
            "example": ["example", "for instance", "such as", "like this", "consider"],
            "problem-solving": ["solve", "solution", "answer", "calculate", "find"],
            "experiment": ["experiment", "test", "try", "hypothesis", "result"],
            "review": ["review", "summary", "recap", "remember", "covered"],
            "introduction": ["today", "going to", "will learn", "introduce", "begin"]
        }
        
        # Count matches for each content type
        type_scores = {}
        for content_type, keywords in content_patterns.items():
            score = sum(1 for keyword in keywords if keyword in transcript_lower)
            type_scores[content_type] = score
        
        # Return the content type with highest score
        if not type_scores or max(type_scores.values()) == 0:
            return "general-content"
        
        return max(type_scores.items(), key=lambda x: x[1])[0]
    
    def create_educational_timeline(self, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create an educational timeline showing content progression"""
        timeline = {
            "total_duration": 0,
            "segments": [],
            "content_distribution": {},
            "key_moments": []
        }
        
        if not scenes:
            return timeline
        
        timeline["total_duration"] = scenes[-1]["end_time"]
        
        # Analyze content distribution
        content_types = {}
        for scene in scenes:
            content_type = scene.get("content_type", "general-content")
            if content_type not in content_types:
                content_types[content_type] = 0
            content_types[content_type] += scene["end_time"] - scene["start_time"]
        
        timeline["content_distribution"] = content_types
        
        # Identify key educational moments (high education score)
        key_moments = []
        for scene in scenes:
            if scene.get("education_score", 0) > 0.7:
                key_moments.append({
                    "time": scene["start_time"],
                    "type": scene.get("content_type", "important"),
                    "description": f"High educational value segment ({scene.get('content_type', 'content')})"
                })
        
        timeline["key_moments"] = key_moments
        timeline["segments"] = scenes
        
        return timeline