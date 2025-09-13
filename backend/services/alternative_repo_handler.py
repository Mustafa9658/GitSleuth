"""Alternative repository handler that downloads ZIP instead of cloning."""

import os
import zipfile
import tempfile
import requests
from pathlib import Path
from typing import List

from core.config import settings
from core.models import FileInfo
from core.exceptions import RepositoryError


class AlternativeRepositoryHandler:
    """Handles repository processing by downloading ZIP files instead of cloning."""
    
    def __init__(self):
        self.temp_dir = Path("./temp_repos")
        self.temp_dir.mkdir(exist_ok=True)
    
    def clone_repository(self, repo_url: str) -> str:
        """
        Download repository as ZIP file instead of cloning.
        
        Args:
            repo_url: GitHub repository URL
            
        Returns:
            Path to the extracted repository
            
        Raises:
            RepositoryError: If download fails
        """
        try:
            # Convert GitHub URL to ZIP download URL
            if "github.com" in repo_url:
                if repo_url.endswith(".git"):
                    repo_url = repo_url[:-4]
                if not repo_url.endswith("/archive/refs/heads/main.zip"):
                    repo_url = repo_url.rstrip("/") + "/archive/refs/heads/main.zip"
            
            # Extract repository name
            # For URL like: https://github.com/user/repo/archive/refs/heads/main.zip
            # We want the repo name which is at position -5
            repo_name = repo_url.split("/")[-5]  # Get repo name from URL
            print(f"🔧 Extracted repo name: {repo_name}")
            repo_path = self.temp_dir / repo_name
            
            # Remove existing directory if it exists
            if repo_path.exists():
                import shutil
                shutil.rmtree(repo_path)
            
            # Download ZIP file
            print(f"Downloading repository: {repo_url}")
            response = requests.get(repo_url, stream=True)
            response.raise_for_status()
            
            # Save ZIP file
            zip_path = self.temp_dir / f"{repo_name}.zip"
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Extract ZIP file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            # Find the extracted directory (it might have a different name)
            print(f"🔧 Looking for extracted directories with '{repo_name}' in name")
            extracted_dirs = [d for d in self.temp_dir.iterdir() if d.is_dir() and repo_name in d.name]
            print(f"🔧 Found directories: {[d.name for d in extracted_dirs]}")
            if extracted_dirs:
                actual_repo_path = extracted_dirs[0]
                print(f"🔧 Found extracted directory: {actual_repo_path}")
                # Rename to expected name
                actual_repo_path.rename(repo_path)
                print(f"🔧 Renamed to: {repo_path}")
            else:
                print(f"⚠️ No extracted directory found with '{repo_name}' in name")
                # List all directories in temp_dir
                all_dirs = [d for d in self.temp_dir.iterdir() if d.is_dir()]
                print(f"🔧 All directories in temp_dir: {[d.name for d in all_dirs]}")
                if all_dirs:
                    # Use the first directory found
                    actual_repo_path = all_dirs[0]
                    print(f"🔧 Using first directory found: {actual_repo_path}")
                    actual_repo_path.rename(repo_path)
                    print(f"🔧 Renamed to: {repo_path}")
            
            # Clean up ZIP file
            zip_path.unlink()
            
            return str(repo_path)
            
        except Exception as e:
            raise RepositoryError(f"Failed to download repository: {e}")
    
    def walk_directory(self, repo_path: str) -> List[FileInfo]:
        """Walk through repository directory and collect file information."""
        files = []
        repo_path = Path(repo_path)
        
        print(f"🔧 Walking directory: {repo_path}")
        print(f"🔧 Directory exists: {repo_path.exists()}")
        print(f"🔧 Is directory: {repo_path.is_dir()}")
        
        if repo_path.exists():
            print(f"🔧 Directory contents: {list(repo_path.iterdir())}")
        
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
                    print(f"🔧 Found file {len(files)}: {file_info.path} ({extension}, {language}, binary: {is_binary})")
                    
                except (OSError, PermissionError):
                    # Skip files that can't be accessed
                    continue
        
        print(f"🔧 Found {len(files)} total files in repository")
        return files
    
    def filter_files(self, files: List[FileInfo]) -> List[FileInfo]:
        """Filter files based on supported extensions and excluded directories."""
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
        """Read content of a file."""
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
        """Clean up temporary repository directory."""
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
            import mimetypes
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
    
    def _get_language_from_extension(self, extension: str) -> str:
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
