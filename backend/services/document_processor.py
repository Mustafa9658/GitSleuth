"""Document processing service for GitSleuth."""

import re
import uuid
from typing import List, Dict, Any
from pathlib import Path

from core.config import settings
from core.models import FileInfo, Chunk
from core.exceptions import IndexingError


class DocumentProcessor:
    """Handles document chunking and processing."""
    
    def __init__(self):
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
    
    def chunk_code_file(self, content: str, file_info: FileInfo) -> List[Chunk]:
        """
        Chunk a code file into smaller pieces.
        
        Args:
            content: File content
            file_info: File information
            
        Returns:
            List of Chunk objects
        """
        print(f"🔧 Chunking file: {file_info.path} (content length: {len(content)})")
        chunks = []
        
        # For now, use simple line-based chunking for all files
        # This is more reliable than complex language-specific chunking
        chunks = self._chunk_simple_lines(content, file_info)
        print(f"🔧 Simple line chunking produced {len(chunks)} chunks")
        
        # If no chunks were created, fall back to generic chunking
        if not chunks:
            print(f"🔧 No chunks from simple chunking, trying generic chunking")
            chunks = self._chunk_generic_file(content, file_info)
            print(f"🔧 Generic chunking produced {len(chunks)} chunks")
        
        print(f"🔧 Generated {len(chunks)} chunks for {file_info.path}")
        if chunks:
            print(f"🔧 First chunk content: '{chunks[0].content[:100]}...'")
        
        return chunks
    
    def _chunk_simple_lines(self, content: str, file_info: FileInfo) -> List[Chunk]:
        """Simple line-based chunking that works for all file types."""
        chunks = []
        lines = content.split('\n')
        
        if not lines:
            return chunks
        
        current_chunk = []
        current_start_line = 1
        
        for i, line in enumerate(lines, 1):
            current_chunk.append(line)
            
            # Create chunk when we reach chunk_size or end of file
            if len('\n'.join(current_chunk)) >= self.chunk_size or i == len(lines):
                chunk_content = '\n'.join(current_chunk)
                if chunk_content.strip():  # Only create chunk if it has content
                    chunks.append(self._create_chunk(
                        chunk_content, file_info, current_start_line, i
                    ))
                
                # Start new chunk
                current_chunk = []
                current_start_line = i + 1
        
        return chunks
    
    def _chunk_python_file(self, content: str, file_info: FileInfo) -> List[Chunk]:
        """Chunk Python file by functions and classes."""
        chunks = []
        lines = content.split('\n')
        
        # Find function and class definitions
        current_chunk = []
        current_start_line = 1
        in_function = False
        indent_level = 0
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Check for class or function definition
            if (stripped.startswith('class ') or stripped.startswith('def ')) and not in_function:
                # Save previous chunk if exists
                if current_chunk:
                    chunk_content = '\n'.join(current_chunk)
                    if len(chunk_content.strip()) > 0:
                        chunks.append(self._create_chunk(
                            chunk_content, file_info, current_start_line, i - 1
                        ))
                
                # Start new chunk
                current_chunk = [line]
                current_start_line = i
                in_function = True
                indent_level = len(line) - len(line.lstrip())
            
            elif in_function:
                # Check if we're still in the same function/class
                current_indent = len(line) - len(line.lstrip())
                if stripped and current_indent <= indent_level:
                    # End of function/class
                    chunk_content = '\n'.join(current_chunk)
                    if len(chunk_content.strip()) > 0:
                        chunks.append(self._create_chunk(
                            chunk_content, file_info, current_start_line, i - 1
                        ))
                    
                    # Reset for next function/class
                    current_chunk = []
                    in_function = False
                else:
                    current_chunk.append(line)
            
            else:
                # Module-level code
                current_chunk.append(line)
                
                # If chunk gets too large, split it
                if len('\n'.join(current_chunk)) > self.chunk_size:
                    chunk_content = '\n'.join(current_chunk)
                    if len(chunk_content.strip()) > 0:
                        chunks.append(self._create_chunk(
                            chunk_content, file_info, current_start_line, i
                        ))
                    current_chunk = []
                    current_start_line = i + 1
        
        # Add remaining content
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            if len(chunk_content.strip()) > 0:
                chunks.append(self._create_chunk(
                    chunk_content, file_info, current_start_line, len(lines)
                ))
        
        return chunks
    
    def _chunk_js_file(self, content: str, file_info: FileInfo) -> List[Chunk]:
        """Chunk JavaScript/TypeScript file by functions and classes."""
        chunks = []
        lines = content.split('\n')
        
        current_chunk = []
        current_start_line = 1
        brace_count = 0
        in_function = False
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Check for function or class definition
            if (stripped.startswith('function ') or 
                stripped.startswith('class ') or 
                '=>' in stripped or
                stripped.startswith('const ') and '=' in stripped and '(' in stripped):
                
                # Save previous chunk if exists
                if current_chunk and not in_function:
                    chunk_content = '\n'.join(current_chunk)
                    if len(chunk_content.strip()) > 0:
                        chunks.append(self._create_chunk(
                            chunk_content, file_info, current_start_line, i - 1
                        ))
                
                # Start new chunk
                current_chunk = [line]
                current_start_line = i
                in_function = True
                brace_count = 0
            
            elif in_function:
                # Count braces to track function boundaries
                brace_count += line.count('{') - line.count('}')
                current_chunk.append(line)
                
                # End of function when braces are balanced
                if brace_count == 0 and stripped:
                    chunk_content = '\n'.join(current_chunk)
                    if len(chunk_content.strip()) > 0:
                        chunks.append(self._create_chunk(
                            chunk_content, file_info, current_start_line, i
                        ))
                    
                    current_chunk = []
                    in_function = False
                    current_start_line = i + 1
            
            else:
                # Module-level code
                current_chunk.append(line)
                
                # If chunk gets too large, split it
                if len('\n'.join(current_chunk)) > self.chunk_size:
                    chunk_content = '\n'.join(current_chunk)
                    if len(chunk_content.strip()) > 0:
                        chunks.append(self._create_chunk(
                            chunk_content, file_info, current_start_line, i
                        ))
                    current_chunk = []
                    current_start_line = i + 1
        
        # Add remaining content
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            if len(chunk_content.strip()) > 0:
                chunks.append(self._create_chunk(
                    chunk_content, file_info, current_start_line, len(lines)
                ))
        
        return chunks
    
    def _chunk_class_based_file(self, content: str, file_info: FileInfo) -> List[Chunk]:
        """Chunk class-based files (Java, C#) by classes and methods."""
        chunks = []
        lines = content.split('\n')
        
        current_chunk = []
        current_start_line = 1
        brace_count = 0
        in_class = False
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Check for class definition
            if (stripped.startswith('class ') or 
                stripped.startswith('public class ') or
                stripped.startswith('private class ')):
                
                # Save previous chunk if exists
                if current_chunk and not in_class:
                    chunk_content = '\n'.join(current_chunk)
                    if len(chunk_content.strip()) > 0:
                        chunks.append(self._create_chunk(
                            chunk_content, file_info, current_start_line, i - 1
                        ))
                
                # Start new chunk
                current_chunk = [line]
                current_start_line = i
                in_class = True
                brace_count = 0
            
            elif in_class:
                # Count braces to track class boundaries
                brace_count += line.count('{') - line.count('}')
                current_chunk.append(line)
                
                # End of class when braces are balanced
                if brace_count == 0 and stripped:
                    chunk_content = '\n'.join(current_chunk)
                    if len(chunk_content.strip()) > 0:
                        chunks.append(self._create_chunk(
                            chunk_content, file_info, current_start_line, i
                        ))
                    
                    current_chunk = []
                    in_class = False
                    current_start_line = i + 1
            
            else:
                # Module-level code
                current_chunk.append(line)
                
                # If chunk gets too large, split it
                if len('\n'.join(current_chunk)) > self.chunk_size:
                    chunk_content = '\n'.join(current_chunk)
                    if len(chunk_content.strip()) > 0:
                        chunks.append(self._create_chunk(
                            chunk_content, file_info, current_start_line, i
                        ))
                    current_chunk = []
                    current_start_line = i + 1
        
        # Add remaining content
        if current_chunk:
            chunk_content = '\n'.join(current_chunk)
            if len(chunk_content.strip()) > 0:
                chunks.append(self._create_chunk(
                    chunk_content, file_info, current_start_line, len(lines)
                ))
        
        return chunks
    
    def _chunk_generic_file(self, content: str, file_info: FileInfo) -> List[Chunk]:
        """Generic chunking for other file types."""
        chunks = []
        
        # Simple character-based chunking
        start = 0
        line_num = 1
        
        while start < len(content):
            end = min(start + self.chunk_size, len(content))
            
            # Try to break at a line boundary
            if end < len(content):
                last_newline = content.rfind('\n', start, end)
                if last_newline > start:
                    end = last_newline + 1
            
            chunk_content = content[start:end].strip()
            if chunk_content:
                # Count lines in this chunk
                chunk_lines = chunk_content.count('\n') + 1
                
                chunks.append(self._create_chunk(
                    chunk_content, file_info, line_num, line_num + chunk_lines - 1
                ))
                
                line_num += chunk_lines
            
            start = end
        
        return chunks
    
    def _create_chunk(self, content: str, file_info: FileInfo, start_line: int, end_line: int) -> Chunk:
        """Create a Chunk object."""
        chunk_id = str(uuid.uuid4())
        
        metadata = {
            "file_path": file_info.path,
            "language": file_info.language,
            "extension": file_info.extension,
            "start_line": start_line,
            "end_line": end_line,
            "chunk_size": len(content)
        }
        
        return Chunk(
            content=content,
            metadata=metadata,
            chunk_id=chunk_id,
            file_path=file_info.path,
            start_line=start_line,
            end_line=end_line
        )
