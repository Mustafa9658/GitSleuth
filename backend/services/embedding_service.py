"""Embedding service for GitSleuth."""

from typing import List
from openai import OpenAI

from core.config import settings
from core.exceptions import LLMError


class EmbeddingService:
    """Handles text embedding generation using OpenAI."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "text-embedding-ada-002"
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            LLMError: If embedding generation fails
        """
        try:
            # Process in batches to avoid rate limits
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                batch_embeddings = [embedding.embedding for embedding in response.data]
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
            
        except Exception as e:
            raise LLMError(f"Failed to create embeddings: {e}")
    
    def create_single_embedding(self, text: str) -> List[float]:
        """
        Create embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
            
        Raises:
            LLMError: If embedding generation fails
        """
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=[text]
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            raise LLMError(f"Failed to create single embedding: {e}")
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this service.
        
        Returns:
            Embedding dimension
        """
        # text-embedding-ada-002 produces 1536-dimensional embeddings
        return 1536
