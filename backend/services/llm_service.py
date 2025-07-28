# backend/app/services/llm_service.py
from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
import asyncio
from config import settings

class LLMService:
    """
    Service for interacting with Large Language Models (OpenAI GPT)
    Handles educational content analysis and generation
    """
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.MAX_TOKENS
    
    async def generate_response(self, prompt: str, system_prompt: str = None) -> str:
        """Generate response using OpenAI GPT"""
        try:
            messages = []
            
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            messages.append({"role": "user", "content": prompt})
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"LLM generation failed: {str(e)}")
            return "Unable to generate response at this time."
    
    async def analyze_educational_content(self, transcript: str) -> Dict[str, Any]:
        """Analyze transcript for educational content structure"""
        system_prompt = """
        You are an educational content analyst. Analyze video transcripts to identify:
        1. Key concepts being taught
        2. Learning objectives
        3. Educational content type (explanation, demonstration, example, etc.)
        4. Difficulty level
        5. Subject area
        """
        
        prompt = f"""
        Analyze this educational video transcript:
        
        "{transcript}"
        
        Provide analysis in JSON format:
        {{
            "key_concepts": ["concept1", "concept2", ...],
            "learning_objectives": ["objective1", "objective2", ...],
            "content_type": "explanation|demonstration|example|problem_solving|review",
            "difficulty_level": "beginner|intermediate|advanced",
            "subject_area": "subject name",
            "educational_value_score": 0.0-1.0
        }}
        """
        
        try:
            response = await self.generate_response(prompt, system_prompt)
            import json
            return json.loads(response)
        except Exception as e:
            print(f"Content analysis failed: {str(e)}")
            return {
                "key_concepts": [],
                "learning_objectives": [],
                "content_type": "general",
                "difficulty_level": "intermediate",
                "subject_area": "general",
                "educational_value_score": 0.5
            }
    
    async def generate_study_questions(self, scene_content: str, difficulty: str = "intermediate") -> List[str]:
        """Generate study questions based on scene content"""
        prompt = f"""
        Based on this educational content, generate 5 study questions at {difficulty} level:
        
        Content: "{scene_content}"
        
        Generate questions that:
        1. Test understanding of key concepts
        2. Encourage critical thinking
        3. Are appropriate for the difficulty level
        4. Help reinforce learning
        
        Return as a simple numbered list.
        """
        
        try:
            response = await self.generate_response(prompt)
            # Parse numbered list
            questions = []
            for line in response.split('\n'):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-')):
                    # Remove numbering/bullets
                    question = line.split('.', 1)[-1].strip()
                    if question:
                        questions.append(question)
            
            return questions[:5]  # Return max 5 questions
            
        except Exception as e:
            print(f"Question generation failed: {str(e)}")
            return []
    
    async def create_learning_summary(self, scenes: List[Dict[str, Any]], video_title: str) -> str:
        """Create a learning summary for a video based on its scenes"""
        scene_descriptions = []
        for i, scene in enumerate(scenes):
            desc = scene.get('description', 'Educational content')
            timestamp = f"{scene.get('start_time', 0):.0f}s"
            scene_descriptions.append(f"{timestamp}: {desc}")
        
        prompt = f"""
        Create a comprehensive learning summary for the educational video "{video_title}".
        
        Scene breakdown:
        {chr(10).join(scene_descriptions)}
        
        Provide:
        1. Overview of what students will learn
        2. Key concepts covered
        3. Learning progression through the video
        4. Recommended follow-up topics
        
        Keep it concise but informative, suitable for students.
        """
        
        try:
            return await self.generate_response(prompt)
        except Exception as e:
            print(f"Summary generation failed: {str(e)}")
            return f"Educational content covering various topics in {video_title}."
    
    async def explain_concept(self, concept: str, context: str = "", level: str = "intermediate") -> str:
        """Generate explanation for a specific concept"""
        system_prompt = f"""
        You are an expert educator. Explain concepts clearly at the {level} level.
        Use analogies, examples, and step-by-step explanations when helpful.
        """
        
        context_part = f" in the context of: {context}" if context else ""
        
        prompt = f"""
        Explain the concept "{concept}"{context_part}.
        
        Make the explanation:
        1. Clear and accessible for {level} learners
        2. Include relevant examples
        3. Highlight key points
        4. Connect to broader understanding
        
        Provide a comprehensive but concise explanation.
        """
        
        try:
            return await self.generate_response(prompt, system_prompt)
        except Exception as e:
            print(f"Concept explanation failed: {str(e)}")
            return f"The concept '{concept}' is an important topic in this subject area."
    
    async def generate_transcript_summary(self, transcript: str, max_length: int = 200) -> str:
        """Generate a concise summary of a transcript"""
        prompt = f"""
        Summarize this educational video transcript in approximately {max_length} characters:
        
        "{transcript}"
        
        Focus on:
        1. Main topic/subject
        2. Key points taught
        3. Learning outcomes
        
        Make it informative and student-friendly.
        """
        
        try:
            summary = await self.generate_response(prompt)
            # Truncate if too long
            if len(summary) > max_length:
                summary = summary[:max_length-3] + "..."
            return summary
        except Exception as e:
            print(f"Summary generation failed: {str(e)}")
            return transcript[:max_length-3] + "..." if len(transcript) > max_length else transcript
    
    async def classify_question_intent(self, query: str) -> Dict[str, Any]:
        """Classify user query to understand their learning intent"""
        prompt = f"""
        Analyze this student question and classify their learning intent:
        
        Question: "{query}"
        
        Classify as JSON:
        {{
            "intent_type": "definition|explanation|example|demonstration|problem_solving|review",
            "specificity": "general|specific|very_specific",
            "urgency": "low|medium|high",
            "cognitive_level": "remember|understand|apply|analyze|evaluate|create",
            "keywords": ["keyword1", "keyword2", ...],
            "suggested_content_types": ["content_type1", "content_type2", ...]
        }}
        """
        
        try:
            response = await self.generate_response(prompt)
            import json
            return json.loads(response)
        except Exception as e:
            print(f"Intent classification failed: {str(e)}")
            return {
                "intent_type": "explanation",
                "specificity": "general",
                "urgency": "medium",
                "cognitive_level": "understand",
                "keywords": query.split(),
                "suggested_content_types": ["explanation", "example"]
            }