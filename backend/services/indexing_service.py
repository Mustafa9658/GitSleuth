"""Indexing service for GitSleuth."""

import asyncio
from typing import List
from pathlib import Path

from core.config import settings
from core.models import SessionStatus
from core.exceptions import IndexingError
from .repo_handler import RepositoryHandler
from .document_processor import DocumentProcessor
from .embedding_service import EmbeddingService
from .vector_store import VectorStore
from .session_manager import SessionManager


class IndexingService:
    """Handles repository indexing process."""
    
    def __init__(self, session_manager: SessionManager, vector_store: VectorStore):
        self.session_manager = session_manager
        self.vector_store = vector_store
        self.repo_handler = RepositoryHandler()
        self.document_processor = DocumentProcessor()
        self.embedding_service = EmbeddingService()
    
    async def index_repository(self, session_id: str, repo_url: str) -> None:
        """
        Index a repository asynchronously.
        
        Args:
            session_id: Session identifier
            repo_url: GitHub repository URL
        """
        try:
            # Update status to indexing
            self.session_manager.update_session(
                session_id, 
                SessionStatus.INDEXING, 
                "Starting repository cloning..."
            )
            
            # Clone repository
            repo_path = self.repo_handler.clone_repository(repo_url)
            print(f"🔧 Repository downloaded to: {repo_path}")
            
            # Update session with repo path
            session = self.session_manager.get_session(session_id)
            session.repo_path = repo_path
            
            # Walk directory and collect files
            self.session_manager.update_session(
                session_id,
                SessionStatus.INDEXING,
                "Scanning repository files...",
                {"step": "scanning_files"}
            )
            
            all_files = self.repo_handler.walk_directory(repo_path)
            print(f"🔧 Found {len(all_files)} total files in repository")
            session.total_files = len(all_files)
            
            # Filter files
            filtered_files = self.repo_handler.filter_files(all_files)
            print(f"🔧 After filtering: {len(filtered_files)} files to process")
            session.total_files = len(filtered_files)
            
            self.session_manager.update_session(
                session_id,
                SessionStatus.INDEXING,
                f"Found {len(filtered_files)} files to process. Starting indexing...",
                {"step": "processing_files", "total_files": len(filtered_files)}
            )
            
            # Create vector store collection
            collection_name = self.vector_store.create_collection(session_id)
            
            # Process files in batches
            batch_size = 10
            all_chunks = []
            
            for i in range(0, len(filtered_files), batch_size):
                batch_files = filtered_files[i:i + batch_size]
                
                # Process batch
                batch_chunks = await self._process_file_batch(batch_files, repo_path)
                all_chunks.extend(batch_chunks)
                
                # Update progress
                session.processed_files = min(i + batch_size, len(filtered_files))
                progress = {
                    "step": "processing_files",
                    "processed_files": session.processed_files,
                    "total_files": session.total_files,
                    "processed_chunks": len(all_chunks)
                }
                
                self.session_manager.update_session(
                    session_id,
                    SessionStatus.INDEXING,
                    f"Processed {session.processed_files}/{session.total_files} files...",
                    progress
                )
            
            # Generate embeddings in batches
            self.session_manager.update_session(
                session_id,
                SessionStatus.INDEXING,
                "Generating embeddings...",
                {"step": "generating_embeddings"}
            )
            
            chunk_texts = [chunk.content for chunk in all_chunks]
            
            # Debug logging
            print(f"🔧 Total chunks created: {len(all_chunks)}")
            if all_chunks:
                print(f"🔧 First chunk content preview: '{all_chunks[0].content[:100]}...'")
                print(f"🔧 First chunk file: {all_chunks[0].file_path}")
                print(f"🔧 First chunk metadata: {all_chunks[0].metadata}")
            
            # Filter out empty chunks
            non_empty_chunks = []
            non_empty_texts = []
            empty_count = 0
            for chunk, text in zip(all_chunks, chunk_texts):
                if text.strip():  # Only include non-empty chunks
                    non_empty_chunks.append(chunk)
                    non_empty_texts.append(text)
                else:
                    empty_count += 1
            
            print(f"🔧 Empty chunks found: {empty_count}")
            print(f"🔧 Non-empty chunks: {len(non_empty_chunks)}")
            
            if not non_empty_texts:
                raise IndexingError("No valid chunks found to process")
            
            print(f"Processing {len(non_empty_texts)} non-empty chunks out of {len(chunk_texts)} total chunks")
            embeddings = self.embedding_service.create_embeddings(non_empty_texts)
            
            # Store in vector database
            self.session_manager.update_session(
                session_id,
                SessionStatus.INDEXING,
                "Storing in vector database...",
                {"step": "storing_vectors"}
            )
            
            self.vector_store.add_chunks(session_id, non_empty_chunks, embeddings)
            
            # Update final status
            session.total_chunks = len(non_empty_chunks)
            session.processed_chunks = len(non_empty_chunks)
            
            self.session_manager.update_session(
                session_id,
                SessionStatus.READY,
                f"Indexing complete! Processed {len(filtered_files)} files and {len(non_empty_chunks)} chunks.",
                {
                    "step": "complete",
                    "total_files": len(filtered_files),
                    "total_chunks": len(non_empty_chunks)
                }
            )
            
        except Exception as e:
            # Update status to error
            self.session_manager.update_session(
                session_id,
                SessionStatus.ERROR,
                f"Indexing failed: {str(e)}"
            )
            
            # Cleanup
            try:
                if hasattr(session, 'repo_path') and session.repo_path:
                    self.repo_handler.cleanup_repository(session.repo_path)
            except:
                pass
            
            raise IndexingError(f"Repository indexing failed: {e}")
    
    async def _process_file_batch(self, files: List, repo_path: str) -> List:
        """
        Process a batch of files.
        
        Args:
            files: List of FileInfo objects
            repo_path: Repository path
            
        Returns:
            List of Chunk objects
        """
        chunks = []
        
        for file_info in files:
            try:
                # Read file content
                full_path = Path(repo_path) / file_info.path
                print(f"🔧 Processing file: {file_info.path}")
                print(f"🔧 Full path: {full_path}")
                print(f"🔧 File language: {file_info.language}")
                print(f"🔧 File extension: {file_info.extension}")
                
                content = self.repo_handler.read_file_content(str(full_path))
                print(f"🔧 File content length: {len(content)}")
                print(f"🔧 File content preview: '{content[:200]}...'")
                
                # Chunk the file
                file_chunks = self.document_processor.chunk_code_file(content, file_info)
                print(f"🔧 Generated {len(file_chunks)} chunks for {file_info.path}")
                
                if file_chunks:
                    print(f"🔧 First chunk content: '{file_chunks[0].content[:100]}...'")
                
                chunks.extend(file_chunks)
                
            except Exception as e:
                # Log error but continue with other files
                print(f"❌ Error processing file {file_info.path}: {e}")
                continue
        
        return chunks
    
    def get_indexing_progress(self, session_id: str) -> dict:
        """
        Get indexing progress for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Progress information
        """
        session = self.session_manager.get_session(session_id)
        
        return {
            "status": session.status.value,
            "message": session.error_message or "Processing...",
            "progress": session.progress,
            "total_files": session.total_files,
            "processed_files": session.processed_files,
            "total_chunks": session.total_chunks,
            "processed_chunks": session.processed_chunks
        }
    
    def cleanup_session(self, session_id: str) -> None:
        """
        Clean up session resources.
        
        Args:
            session_id: Session identifier
        """
        try:
            session = self.session_manager.get_session(session_id)
            
            # Cleanup repository
            if session.repo_path:
                self.repo_handler.cleanup_repository(session.repo_path)
            
            # Cleanup vector store
            self.vector_store.delete_collection(session_id)
            
            # Delete session
            self.session_manager.delete_session(session_id)
            
        except Exception as e:
            print(f"Error cleaning up session {session_id}: {e}")
