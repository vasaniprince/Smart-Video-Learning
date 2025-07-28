from openai import AsyncOpenAI
import numpy as np
from typing import List, Dict, Any
import asyncio
from sentence_transformers import SentenceTransformer
import os

from config import settings

class EmbeddingGenerator:
    """
    Handles generation of embeddings for semantic search
    Supports both OpenAI embeddings and local sentence transformers
    """
    
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.use_openai = bool(self.openai_api_key)
        
        if self.use_openai:
            self.client = AsyncOpenAI(api_key=self.openai_api_key)
            self.model_name = "text-embedding-ada-002"
        else:
            # Fallback to local sentence transformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for given text"""
        if not text.strip():
            # Return zero embedding for empty text
            return [0.0] * 384  # Default dimension
        
        try:
            if self.use_openai:
                return await self._generate_openai_embedding(text)
            else:
                return await self._generate_local_embedding(text)
        except Exception as e:
            print(f"Embedding generation failed: {str(e)}")
            # Return random embedding as fallback
            return np.random.rand(384).tolist()
    
    async def _generate_openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API"""
        response = await self.client.embeddings.create(
            model=self.model_name,
            input=text
        )
        return response.data[0].embedding
    
    async def _generate_local_embedding(self, text: str) -> List[float]:
        """Generate embedding using local sentence transformer"""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None, 
            lambda: self.model.encode(text)
        )
        return embedding.tolist()
    
    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts efficiently"""
        if self.use_openai:
            # OpenAI supports batch processing
            response = await self.client.embeddings.create(
                model=self.model_name,
                input=texts
            )
            return [item.embedding for item in response.data]
        else:
            # Use local model for batch processing
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self.model.encode(texts)
            )
            return embeddings.tolist()