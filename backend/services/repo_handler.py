"""Repository handling service for GitSleuth."""

import os
import git
import mimetypes
from pathlib import Path
from typing import List, Optional
from git import Repo, InvalidGitRepositoryError

from core.config import settings
from core.models import FileInfo
from core.exceptions import RepositoryError


class RepositoryHandler:
    """Handles repository cloning and file processing."""
    
    def __init__(self):
        self.temp_dir = Path("./temp_repos")
        self.temp_dir.mkdir(exist_ok=True)
    
    def clone_repository(self, repo_url: str) -> str:
        """
        Clone a GitHub repository to a temporary directory.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Path to the cloned repository
            
        Raises:
            RepositoryError: If cloning fails
        """
        try:
            import shutil
            import stat
            
            # Extract repository name from URL
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            repo_path = self.temp_dir / repo_name
            
            # Remove existing directory if it exists (with Windows permission handling)
            if repo_path.exists():
                self._remove_readonly_files(repo_path)
                shutil.rmtree(repo_path)
            
            # Clone the repository
            repo = Repo.clone_from(repo_url, repo_path)
            
            return str(repo_path)
            
        except InvalidGitRepositoryError as e:
            raise RepositoryError(f"Invalid Git repository: {e}")
        except Exception as e:
            raise RepositoryError(f"Failed to clone repository: {e}")
    
    def _remove_readonly_files(self, path):
        """Remove read-only files on Windows."""
        import os
        import stat
        
        for root, dirs, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    os.chmod(file_path, stat.S_IWRITE)
                except:
                    pass
    
    def walk_directory(self, repo_path: str) -> List[FileInfo]:
        """
        Walk through repository directory and collect file information.
        
        Args:
            repo_path: Path to the repository
            
        Returns:
            List of FileInfo objects
        """
        files = []
        repo_path = Path(repo_path)
        
        for file_path in repo_path.rglob("*"):
            if file_path.is_file():
                try:
                    # Get file size
                    file_size = file_path.stat().st_size
                    
                    # Skip if file is too large
                    if file_size > settings.max_file_size:
                        continue
                    
                    # Get file extension
                    extension = file_path.suffix.lower()
                    
                    # Check if file is binary
                    is_binary = self._is_binary_file(file_path)
                    
                    # Determine language from extension
                    language = self._get_language_from_extension(extension)
                    
                    file_info = FileInfo(
                        path=str(file_path.relative_to(repo_path)),
                        size=file_size,
                        extension=extension,
                        language=language,
                        is_binary=is_binary
                    )
                    
                    files.append(file_info)
                    
                except (OSError, PermissionError):
                    # Skip files that can't be accessed
                    continue
        
        return files
    
    def filter_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """
        Filter files based on supported extensions and excluded directories.
        
        Args:
            files: List of FileInfo objects
            
        Returns:
            Filtered list of FileInfo objects
        """
        filtered_files = []
        
        for file_info in files:
            # Skip if file is binary
            if file_info.is_binary:
                continue
            
            # Skip if extension not supported
            if file_info.extension not in settings.supported_extensions:
                continue
            
            # Skip if in excluded directory
            if self._is_in_excluded_directory(file_info.path):
                continue
            
            # Skip if too many files already
            if len(filtered_files) >= settings.max_files_per_repo:
                break
            
            filtered_files.append(file_info)
        
        return filtered_files
    
    def read_file_content(self, file_path: str) -> str:
        """
        Read content of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File content as string
            
        Raises:
            RepositoryError: If file cannot be read
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                raise RepositoryError(f"Failed to read file {file_path}: {e}")
        except Exception as e:
            raise RepositoryError(f"Failed to read file {file_path}: {e}")
    
    def cleanup_repository(self, repo_path: str) -> None:
        """
        Clean up temporary repository directory.
        
        Args:
            repo_path: Path to the repository to clean up
        """
        try:
            import shutil
            if os.path.exists(repo_path):
                shutil.rmtree(repo_path)
        except Exception:
            # Ignore cleanup errors
            pass
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary."""
        try:
            # Check MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and not mime_type.startswith('text/'):
                return True
            
            # Check file extension
            binary_extensions = {'.exe', '.dll', '.so', '.dylib', '.bin', '.img', '.iso'}
            if file_path.suffix.lower() in binary_extensions:
                return True
            
            # Check first 1024 bytes for null bytes
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
                
        except Exception:
            return True
    
    def _get_language_from_extension(self, extension: str) -> Optional[str]:
        """Get programming language from file extension."""
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.md': 'markdown',
            '.txt': 'text',
            '.yml': 'yaml',
            '.yaml': 'yaml',
            '.json': 'json',
            '.xml': 'xml',
            '.sql': 'sql'
        }
        return language_map.get(extension)
    
    def _is_in_excluded_directory(self, file_path: str) -> bool:
        """Check if file is in an excluded directory."""
        path_parts = Path(file_path).parts
        for part in path_parts:
            if part in settings.excluded_dirs:
                return True
        return False
