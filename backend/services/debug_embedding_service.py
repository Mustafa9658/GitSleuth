"""Debug embedding service for GitSleuth."""

from typing import List
from openai import OpenAI

from core.config import settings
from core.exceptions import LLMError


class DebugEmbeddingService:
    """Debug version of embedding service with detailed logging."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "text-embedding-ada-002"
        print(f"🔧 Debug Embedding Service initialized with API key: {settings.openai_api_key[:20]}...")
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Create embeddings for a list of texts with debug logging.
        """
        print(f"🔧 Creating embeddings for {len(texts)} texts")
        
        if not texts:
            print("⚠️ No texts provided for embedding")
            return []
        
        # Check for empty texts
        empty_texts = [i for i, text in enumerate(texts) if not text.strip()]
        if empty_texts:
            print(f"⚠️ Found {len(empty_texts)} empty texts at indices: {empty_texts}")
        
        try:
            # Process in batches to avoid rate limits
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                print(f"🔧 Processing batch {i//batch_size + 1}: {len(batch)} texts")
                
                # Filter out empty texts
                non_empty_batch = [text for text in batch if text.strip()]
                if len(non_empty_batch) != len(batch):
                    print(f"⚠️ Filtered out {len(batch) - len(non_empty_batch)} empty texts")
                
                if not non_empty_batch:
                    print("⚠️ Batch is empty after filtering, skipping")
                    continue
                
                print(f"🔧 Calling OpenAI API with {len(non_empty_batch)} texts")
                response = self.client.embeddings.create(
                    model=self.model,
                    input=non_empty_batch
                )
                
                print(f"🔧 Received response with {len(response.data)} embeddings")
                batch_embeddings = [embedding.embedding for embedding in response.data]
                print(f"🔧 First embedding dimension: {len(batch_embeddings[0]) if batch_embeddings else 'N/A'}")
                
                all_embeddings.extend(batch_embeddings)
            
            print(f"🔧 Total embeddings created: {len(all_embeddings)}")
            return all_embeddings
            
        except Exception as e:
            print(f"❌ Embedding creation failed: {e}")
            raise LLMError(f"Failed to create embeddings: {e}")
    
    def create_single_embedding(self, text: str) -> List[float]:
        """Create embedding for a single text with debug logging."""
        print(f"🔧 Creating single embedding for text: '{text[:50]}...'")
        
        if not text.strip():
            print("⚠️ Empty text provided for single embedding")
            return []
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=[text]
            )
            
            embedding = response.data[0].embedding
            print(f"🔧 Single embedding created with {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            print(f"❌ Single embedding failed: {e}")
            raise LLMError(f"Failed to create single embedding: {e}")
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this service."""
        return 1536
