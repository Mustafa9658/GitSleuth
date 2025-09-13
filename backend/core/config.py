"""Configuration management for GitSleuth backend."""

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    openai_api_key: str = ""
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Vector Store Configuration
    chroma_persist_directory: str = "./chroma_db"
    
    # File Processing Configuration
    max_file_size: int = 1000000  # 1MB
    max_files_per_repo: int = 1000
    
    # Supported file extensions
    supported_extensions: List[str] = [
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", 
        ".cpp", ".c", ".h", ".hpp", ".cs", ".php", ".rb", ".swift",
        ".md", ".txt", ".yml", ".yaml", ".json", ".xml", ".sql"
    ]
    
    # Excluded directories
    excluded_dirs: List[str] = [
        "node_modules", ".git", "dist", "build", "__pycache__", 
        ".pytest_cache", ".venv", "venv", "env", ".env",
        "target", "bin", "obj", ".vs", ".idea", ".vscode"
    ]
    
    # Chunking Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    
    # RAG Configuration
    max_context_chunks: int = 12  # Increased for better project understanding
    similarity_threshold: float = 0.15  # Lowered to get more diverse contexts
    
    # Environment Configuration
    environment: str = "development"
    debug: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
