"""Session management service for GitSleuth."""

import uuid
from typing import Dict, Optional
from datetime import datetime, timedelta

from core.models import SessionStatus
from core.exceptions import SessionNotFoundError


class Session:
    """Represents a user session."""
    
    def __init__(self, session_id: str, repo_url: str):
        self.id = session_id
        self.repo_url = repo_url
        self.status = SessionStatus.IDLE
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.progress = {}
        self.error_message = None
        self.repo_path = None
        self.total_files = 0
        self.processed_files = 0
        self.total_chunks = 0
        self.processed_chunks = 0
    
    def update_status(self, status: SessionStatus, message: str = None, progress: Dict = None):
        """Update session status and progress."""
        self.status = status
        self.updated_at = datetime.now()
        if message:
            self.error_message = message
        if progress:
            self.progress.update(progress)
    
    def is_expired(self, max_age_hours: int = 24) -> bool:
        """Check if session has expired."""
        return datetime.now() - self.created_at > timedelta(hours=max_age_hours)


class SessionManager:
    """Manages user sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.max_age_hours = 24
    
    def create_session(self, repo_url: str) -> str:
        """
        Create a new session.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        session = Session(session_id, repo_url)
        self.sessions[session_id] = session
        return session_id
    
    def get_session(self, session_id: str) -> Session:
        """
        Get a session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session object
            
        Raises:
            SessionNotFoundError: If session not found
        """
        session = self.sessions.get(session_id)
        if not session:
            raise SessionNotFoundError(f"Session {session_id} not found")
        
        # Check if session has expired
        if session.is_expired(self.max_age_hours):
            del self.sessions[session_id]
            raise SessionNotFoundError(f"Session {session_id} has expired")
        
        return session
    
    def update_session(self, session_id: str, status: SessionStatus, 
                      message: str = None, progress: Dict = None) -> None:
        """
        Update session status and progress.
        
        Args:
            session_id: Session identifier
            status: New status
            message: Optional message
            progress: Optional progress information
        """
        session = self.get_session(session_id)
        session.update_status(status, message, progress)
    
    def delete_session(self, session_id: str) -> None:
        """
        Delete a session.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def cleanup_expired_sessions(self) -> int:
        """
        Clean up expired sessions.
        
        Returns:
            Number of sessions cleaned up
        """
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired(self.max_age_hours)
        ]
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
        
        return len(expired_sessions)
    
    def get_session_count(self) -> int:
        """Get total number of active sessions."""
        return len(self.sessions)
    
    def get_session_stats(self) -> Dict[str, int]:
        """Get session statistics."""
        stats = {
            "total": len(self.sessions),
            "idle": 0,
            "indexing": 0,
            "ready": 0,
            "error": 0
        }
        
        for session in self.sessions.values():
            stats[session.status.value] += 1
        
        return stats
