"""Simple in-memory vector store fallback for GitSleuth."""

import numpy as np
from typing import List, Dict, Any, Optional
import uuid
from sklearn.metrics.pairwise import cosine_similarity

from core.config import settings
from core.models import Chunk, Context
from core.exceptions import VectorStoreError


class SimpleVectorStore:
    """Simple in-memory vector store using numpy and sklearn."""
    
    def __init__(self):
        self.collections = {}
        self.embeddings = {}
        self.metadata = {}
    
    def create_collection(self, session_id: str) -> str:
        """
        Create a new collection for a session.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Collection name
        """
        try:
            collection_name = f"repo_{session_id}"
            
            # Initialize collection data
            self.collections[session_id] = {
                "name": collection_name,
                "embeddings": [],
                "chunks": [],
                "metadata": []
            }
            
            return collection_name
            
        except Exception as e:
            raise VectorStoreError(f"Failed to create collection: {e}")
    
    def add_chunks(self, session_id: str, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """
        Add chunks to the vector store.
        
        Args:
            session_id: Session identifier
            chunks: List of chunks to add
            embeddings: List of embeddings for the chunks
        """
        try:
            if session_id not in self.collections:
                raise VectorStoreError(f"Collection not found for session {session_id}")
            
            collection = self.collections[session_id]
            
            # Add embeddings and chunks
            collection["embeddings"].extend(embeddings)
            collection["chunks"].extend(chunks)
            
            # Add metadata
            for chunk in chunks:
                collection["metadata"].append(chunk.metadata)
            
        except Exception as e:
            raise VectorStoreError(f"Failed to add chunks: {e}")
    
    def search_similar(self, session_id: str, query_embedding: List[float], 
                      top_k: int = 5, threshold: float = 0.7) -> List[Context]:
        """
        Search for similar chunks.
        
        Args:
            session_id: Session identifier
            query_embedding: Query embedding vector
            top_k: Number of results to return
            threshold: Similarity threshold
            
        Returns:
            List of Context objects
        """
        try:
            if session_id not in self.collections:
                raise VectorStoreError(f"Collection not found for session {session_id}")
            
            collection = self.collections[session_id]
            
            if not collection["embeddings"]:
                return []
            
            # Convert to numpy arrays
            query_emb = np.array(query_embedding).reshape(1, -1)
            doc_embeddings = np.array(collection["embeddings"])
            
            # Calculate cosine similarities
            similarities = cosine_similarity(query_emb, doc_embeddings)[0]
            
            # Get top-k indices
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            contexts = []
            for idx in top_indices:
                similarity_score = similarities[idx]
                
                if similarity_score >= threshold:
                    chunk = collection["chunks"][idx]
                    context = Context(
                        content=chunk.content,
                        file_path=chunk.file_path,
                        similarity_score=float(similarity_score),
                        start_line=chunk.start_line,
                        end_line=chunk.end_line
                    )
                    contexts.append(context)
            
            return contexts
            
        except Exception as e:
            raise VectorStoreError(f"Failed to search similar chunks: {e}")
    
    def get_collection_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics about a collection.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with collection statistics
        """
        try:
            if session_id not in self.collections:
                return {"count": 0, "error": "Collection not found"}
            
            collection = self.collections[session_id]
            count = len(collection["chunks"])
            return {"count": count}
            
        except Exception as e:
            return {"count": 0, "error": str(e)}
    
    def delete_collection(self, session_id: str) -> None:
        """
        Delete a collection.
        
        Args:
            session_id: Session identifier
        """
        try:
            if session_id in self.collections:
                del self.collections[session_id]
                
        except Exception as e:
            raise VectorStoreError(f"Failed to delete collection: {e}")
    
    def cleanup_old_collections(self, max_age_hours: int = 24) -> None:
        """
        Clean up old collections.
        
        Args:
            max_age_hours: Maximum age of collections in hours
        """
        # Simple implementation - just clear all collections
        # In a real implementation, you'd track creation times
        pass
