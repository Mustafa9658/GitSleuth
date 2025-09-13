"""Pydantic models for GitSleuth API."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class SessionStatus(str, Enum):
    """Session status enumeration."""
    IDLE = "idle"
    INDEXING = "indexing"
    READY = "ready"
    ERROR = "error"


class FileInfo(BaseModel):
    """Information about a file in the repository."""
    path: str
    size: int
    extension: str
    language: Optional[str] = None
    is_binary: bool = False


class Chunk(BaseModel):
    """A chunk of processed code."""
    content: str
    metadata: Dict[str, Any]
    chunk_id: str
    file_path: str
    start_line: int
    end_line: int


class Context(BaseModel):
    """Context retrieved for answering a question."""
    content: str
    file_path: str
    similarity_score: float
    start_line: int
    end_line: int


class SourceReference(BaseModel):
    """Source file reference in an answer."""
    file: str
    snippet: str
    line_start: int
    line_end: int


# Request Models
class IndexRequest(BaseModel):
    """Request to index a repository."""
    repo_url: str = Field(..., description="GitHub repository URL")


class QueryRequest(BaseModel):
    """Request to query the codebase."""
    session_id: str = Field(..., description="Session ID")
    question: str = Field(..., description="Question about the codebase")


# Response Models
class IndexResponse(BaseModel):
    """Response for repository indexing."""
    message: str
    session_id: str
    status: SessionStatus = SessionStatus.INDEXING


class StatusResponse(BaseModel):
    """Response for status check."""
    status: SessionStatus
    message: str
    progress: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Response for codebase query."""
    answer: str
    sources: List[SourceReference]
    confidence: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None
