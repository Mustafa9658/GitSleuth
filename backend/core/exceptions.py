"""Custom exceptions for GitSleuth."""


class GitSleuthException(Exception):
    """Base exception for GitSleuth."""
    pass


class RepositoryError(GitSleuthException):
    """Error related to repository operations."""
    pass


class IndexingError(GitSleuthException):
    """Error during repository indexing."""
    pass


class QueryError(GitSleuthException):
    """Error during query processing."""
    pass


class SessionNotFoundError(GitSleuthException):
    """Session not found error."""
    pass


class VectorStoreError(GitSleuthException):
    """Error related to vector store operations."""
    pass


class LLMError(GitSleuthException):
    """Error related to LLM operations."""
    pass
