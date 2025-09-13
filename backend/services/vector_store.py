"""Vector store service for GitSleuth."""

import chromadb
from typing import List, Dict, Any, Optional
import uuid
import os

from core.config import settings
from core.models import Chunk, Context
from core.exceptions import VectorStoreError


class VectorStore:
    """Handles vector storage and retrieval using ChromaDB."""
    
    def __init__(self):
        # Create persist directory if it doesn't exist
        os.makedirs(settings.chroma_persist_directory, exist_ok=True)
        
        # Use the new ChromaDB client API
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory
        )
        self.collections = {}
    
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
            
            # Delete existing collection if it exists
            try:
                self.client.delete_collection(collection_name)
            except:
                pass
            
            # Create new collection with the new API
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": f"Repository analysis for session {session_id}"}
            )
            
            self.collections[session_id] = collection
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
            collection = self.collections.get(session_id)
            if not collection:
                raise VectorStoreError(f"Collection not found for session {session_id}")
            
            # Validate inputs
            if not chunks:
                raise VectorStoreError("No chunks provided")
            
            if not embeddings:
                raise VectorStoreError("No embeddings provided")
            
            if len(chunks) != len(embeddings):
                raise VectorStoreError(f"Mismatch between chunks ({len(chunks)}) and embeddings ({len(embeddings)})")
            
            # Filter out empty embeddings
            valid_chunks = []
            valid_embeddings = []
            for chunk, embedding in zip(chunks, embeddings):
                if embedding and len(embedding) > 0:
                    valid_chunks.append(chunk)
                    valid_embeddings.append(embedding)
            
            if not valid_chunks:
                raise VectorStoreError("No valid embeddings found")
            
            print(f"Adding {len(valid_chunks)} chunks with valid embeddings to vector store")
            
            # Prepare data for ChromaDB
            ids = [chunk.chunk_id for chunk in valid_chunks]
            documents = [chunk.content for chunk in valid_chunks]
            metadatas = [chunk.metadata for chunk in valid_chunks]
            
            # Add to collection
            collection.add(
                ids=ids,
                documents=documents,
                embeddings=valid_embeddings,
                metadatas=metadatas
            )
            
        except Exception as e:
            raise VectorStoreError(f"Failed to add chunks: {e}")
    
    def search_similar(self, session_id: str, query_embedding: List[float], 
                      top_k: int = 5, threshold: float = 0.7, 
                      file_types: List[str] = None, exclude_files: List[str] = None) -> List[Context]:
        """
        Search for similar chunks with enhanced filtering options.
        
        Args:
            session_id: Session identifier
            query_embedding: Query embedding vector
            top_k: Number of results to return
            threshold: Similarity threshold
            file_types: Optional list of file extensions to include
            exclude_files: Optional list of file patterns to exclude
            
        Returns:
            List of Context objects
        """
        try:
            collection = self.collections.get(session_id)
            if not collection:
                raise VectorStoreError(f"Collection not found for session {session_id}")
            
            # Build where clause for metadata filtering
            where_clause = {}
            if file_types:
                where_clause["file_type"] = {"$in": file_types}
            
            # Search for similar chunks with metadata filtering
            query_kwargs = {
                "query_embeddings": [query_embedding],
                "n_results": min(top_k * 2, 50),  # Get more results for filtering
                "include": ["documents", "metadatas", "distances"]
            }
            
            if where_clause:
                query_kwargs["where"] = where_clause
            
            results = collection.query(**query_kwargs)
            
            contexts = []
            if results["documents"] and results["documents"][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results["documents"][0],
                    results["metadatas"][0],
                    results["distances"][0]
                )):
                    # Convert distance to similarity score (ChromaDB uses cosine distance)
                    similarity_score = 1 - distance
                    
                    if similarity_score >= threshold:
                        file_path = metadata.get("file_path", "")
                        
                        # Apply exclude filters
                        if exclude_files:
                            if any(exclude_pattern in file_path for exclude_pattern in exclude_files):
                                continue
                        
                        context = Context(
                            content=doc,
                            file_path=file_path,
                            similarity_score=similarity_score,
                            start_line=metadata.get("start_line", 0),
                            end_line=metadata.get("end_line", 0)
                        )
                        contexts.append(context)
            
            # Sort by similarity score and return top_k
            contexts.sort(key=lambda x: x.similarity_score, reverse=True)
            return contexts[:top_k]
            
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
            collection = self.collections.get(session_id)
            if not collection:
                return {"count": 0, "error": "Collection not found"}
            
            count = collection.count()
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
            collection_name = f"repo_{session_id}"
            self.client.delete_collection(collection_name)
            
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
        try:
            # This is a simplified cleanup - in production you'd want
            # to track creation times and clean up based on age
            collections = self.client.list_collections()
            for collection in collections:
                # For now, just clean up collections that are very old
                # In a real implementation, you'd check creation time
                pass
                
        except Exception as e:
            # Don't raise error for cleanup failures
            pass
