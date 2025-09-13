"""Main FastAPI application for GitSleuth."""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.models import (
    IndexRequest, IndexResponse, StatusResponse, QueryRequest, QueryResponse,
    ErrorResponse, SessionStatus
)
from core.exceptions import (
    SessionNotFoundError, RepositoryError, IndexingError, QueryError
)
from services.session_manager import SessionManager
from services.vector_store import VectorStore
from services.simple_vector_store import SimpleVectorStore
from services.embedding_service import EmbeddingService
from services.debug_embedding_service import DebugEmbeddingService
from services.rag_pipeline import RAGPipeline
from services.indexing_service import IndexingService
from services.alternative_repo_handler import AlternativeRepositoryHandler
from services.rate_limiter import rate_limiter
from services.advanced_cache import advanced_cache
from services.fast_response import fast_response_optimizer


# Global services
session_manager = SessionManager()

# Try ChromaDB first, fallback to simple vector store
try:
    vector_store = VectorStore()
    print("✅ Using ChromaDB vector store")
except Exception as e:
    print(f"⚠️ ChromaDB failed, using simple vector store: {e}")
    vector_store = SimpleVectorStore()

# Use alternative repository handler to avoid Git cloning issues
print("✅ Using alternative repository handler (ZIP download)")

embedding_service = DebugEmbeddingService()
rag_pipeline = RAGPipeline(embedding_service, vector_store)

# Create indexing service with alternative handler
from services.indexing_service import IndexingService
indexing_service = IndexingService(session_manager, vector_store)
indexing_service.repo_handler = AlternativeRepositoryHandler()
indexing_service.embedding_service = embedding_service  # Use the debug embedding service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print("Starting GitSleuth backend...")
    
    # Start cache cleanup task
    await advanced_cache.ensure_cleanup_task()
    
    yield
    
    # Shutdown
    print("Shutting down GitSleuth backend...")
    
    # Cancel cleanup task
    if advanced_cache.cleanup_task and not advanced_cache.cleanup_task.done():
        advanced_cache.cleanup_task.cancel()
        try:
            await advanced_cache.cleanup_task
        except asyncio.CancelledError:
            pass


# Create FastAPI app
app = FastAPI(
    title="GitSleuth API",
    description="RAG-based GitHub repository analysis tool",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SessionNotFoundError)
async def session_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(error="Session not found", detail=str(exc)).dict()
    )


@app.exception_handler(RepositoryError)
async def repository_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(error="Repository error", detail=str(exc)).dict()
    )


@app.exception_handler(IndexingError)
async def indexing_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Indexing error", detail=str(exc)).dict()
    )


@app.exception_handler(QueryError)
async def query_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Query error", detail=str(exc)).dict()
    )


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "GitSleuth API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "sessions": session_manager.get_session_count()
    }


@app.post("/index", response_model=IndexResponse)
async def index_repository(request: IndexRequest, background_tasks: BackgroundTasks):
    """
    Start indexing a GitHub repository.
    
    Args:
        request: IndexRequest with repository URL
        
    Returns:
        IndexResponse with session ID
    """
    try:
        # Validate repository URL
        if not request.repo_url.startswith(("https://github.com/", "git@github.com:")):
            raise HTTPException(
                status_code=400,
                detail="Invalid repository URL. Must be a GitHub repository."
            )
        
        # Create session
        session_id = session_manager.create_session(request.repo_url)
        
        # Start indexing in background
        background_tasks.add_task(
            indexing_service.index_repository,
            session_id,
            request.repo_url
        )
        
        return IndexResponse(
            message="Repository indexing started.",
            session_id=session_id,
            status=SessionStatus.INDEXING
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{session_id}", response_model=StatusResponse)
async def get_status(session_id: str):
    """
    Get indexing status for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        StatusResponse with current status
    """
    try:
        session = session_manager.get_session(session_id)
        
        # Get detailed progress if indexing
        if session.status == SessionStatus.INDEXING:
            progress = indexing_service.get_indexing_progress(session_id)
            return StatusResponse(
                status=session.status,
                message=progress.get("message", "Processing..."),
                progress=progress.get("progress", {})
            )
        
        return StatusResponse(
            status=session.status,
            message=session.error_message or f"Status: {session.status.value}"
        )
        
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
async def query_codebase(request: Request, query_request: QueryRequest):
    """
    Query the indexed codebase with rate limiting and fast response optimization.
    
    Args:
        request: FastAPI request object for rate limiting
        query_request: QueryRequest with session ID and question
        
    Returns:
        QueryResponse with answer and sources
    """
    try:
        # Rate limiting check
        is_allowed, rate_info = rate_limiter.is_allowed(request, "query")
        if not is_allowed:
            headers = rate_limiter.get_rate_limit_headers(rate_info)
            raise HTTPException(
                status_code=429,
                detail=rate_info["error"],
                headers=headers
            )
        
        # Validate session exists and is ready
        session = session_manager.get_session(query_request.session_id)
        
        if session.status != SessionStatus.READY:
            raise HTTPException(
                status_code=400,
                detail=f"Session not ready. Current status: {session.status.value}"
            )
        
        # Process query with fast response optimization
        response = rag_pipeline.query(query_request.question, query_request.session_id)
        
        # Add rate limit headers to response
        headers = rate_limiter.get_rate_limit_headers(rate_info)
        
        return response
        
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/{session_id}/clear-cache")
async def clear_session_cache(session_id: str):
    """
    Clear knowledge cache for a session without deleting the session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Success message
    """
    try:
        rag_pipeline.clear_session_cache(session_id)
        return {"message": "Session cache cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear session cache: {e}")


@app.get("/session/{session_id}/chat-history")
async def get_chat_history(session_id: str):
    """
    Get chat history for a session.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Chat history
    """
    try:
        history = rag_pipeline.get_chat_history(session_id)
        return {"session_id": session_id, "chat_history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get chat history: {e}")


@app.get("/performance/stats")
async def get_performance_stats():
    """
    Get system performance statistics.
    
    Returns:
        Performance metrics and cache statistics
    """
    try:
        cache_stats = advanced_cache.get_stats()
        response_stats = fast_response_optimizer.get_performance_stats()
        
        return {
            "cache_performance": cache_stats,
            "response_optimization": response_stats,
            "rate_limits": {
                "query": rate_limiter.limits["query"].__dict__,
                "index": rate_limiter.limits["index"].__dict__,
                "health": rate_limiter.limits["health"].__dict__
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance stats: {e}")


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    Delete a session and clean up resources.
    
    Args:
        session_id: Session identifier
        
    Returns:
        Success message
    """
    try:
        indexing_service.cleanup_session(session_id)
        # Also clear knowledge cache for this session
        rag_pipeline.clear_session_cache(session_id)
        return {"message": "Session deleted successfully"}
        
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions")
async def list_sessions():
    """
    List all active sessions.
    
    Returns:
        List of sessions with basic info
    """
    try:
        stats = session_manager.get_session_stats()
        return {
            "total_sessions": stats["total"],
            "status_breakdown": stats,
            "sessions": [
                {
                    "id": session_id,
                    "repo_url": session.repo_url,
                    "status": session.status.value,
                    "created_at": session.created_at.isoformat(),
                    "total_files": session.total_files,
                    "total_chunks": session.total_chunks
                }
                for session_id, session in session_manager.sessions.items()
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
