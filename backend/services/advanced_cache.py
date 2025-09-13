"""Advanced multi-level caching system for GitSleuth."""

import time
import hashlib
import json
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import pickle
import threading
from collections import OrderedDict


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: float
    last_accessed: float
    access_count: int
    ttl: float
    size_bytes: int


class LRUCache:
    """Thread-safe LRU cache with size limits."""
    
    def __init__(self, max_size: int = 1000, max_memory_mb: int = 100):
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.current_memory = 0
        self.lock = threading.RLock()
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired."""
        return time.time() - entry.created_at > entry.ttl
    
    def _evict_lru(self):
        """Evict least recently used entries."""
        while (len(self.cache) >= self.max_size or 
               self.current_memory >= self.max_memory_bytes):
            if not self.cache:
                break
            
            # Remove least recently used
            key, entry = self.cache.popitem(last=False)
            self.current_memory -= entry.size_bytes
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self.lock:
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            
            # Check if expired
            if self._is_expired(entry):
                del self.cache[key]
                self.current_memory -= entry.size_bytes
                return None
            
            # Update access info
            entry.last_accessed = time.time()
            entry.access_count += 1
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl: float = 3600) -> None:
        """Set value in cache."""
        with self.lock:
            # Calculate size
            try:
                size_bytes = len(pickle.dumps(value))
            except:
                size_bytes = 1024  # Default estimate
            
            # Remove existing entry if present
            if key in self.cache:
                old_entry = self.cache[key]
                self.current_memory -= old_entry.size_bytes
                del self.cache[key]
            
            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                access_count=1,
                ttl=ttl,
                size_bytes=size_bytes
            )
            
            # Evict if necessary
            self._evict_lru()
            
            # Add new entry
            self.cache[key] = entry
            self.current_memory += size_bytes
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                del self.cache[key]
                self.current_memory -= entry.size_bytes
                return True
            return False
    
    def clear(self):
        """Clear all entries."""
        with self.lock:
            self.cache.clear()
            self.current_memory = 0
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_accesses = sum(entry.access_count for entry in self.cache.values())
            avg_accesses = total_accesses / len(self.cache) if self.cache else 0
            
            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "memory_used_mb": self.current_memory / (1024 * 1024),
                "memory_limit_mb": self.max_memory_bytes / (1024 * 1024),
                "total_accesses": total_accesses,
                "avg_accesses_per_entry": avg_accesses
            }


class AdvancedCache:
    """Multi-level caching system for fast responses."""
    
    def __init__(self):
        # L1: In-memory LRU cache (fastest)
        self.l1_cache = LRUCache(max_size=500, max_memory_mb=50)
        
        # L2: File-based cache (persistent)
        self.l2_cache_dir = Path("./cache")
        self.l2_cache_dir.mkdir(exist_ok=True)
        
        # L3: Session-specific cache
        self.session_caches: Dict[str, LRUCache] = {}
        
        # Cache configurations
        self.ttl_configs = {
            "query_response": 7200,  # 2 hours
            "embedding": 86400,      # 24 hours
            "context": 3600,         # 1 hour
            "session_data": 1800,    # 30 minutes
            "repo_metadata": 86400   # 24 hours
        }
        
        # Background cleanup task
        self.cleanup_task = None
        self._cleanup_started = False
    
    def _generate_key(self, cache_type: str, *args) -> str:
        """Generate cache key from arguments."""
        key_data = f"{cache_type}:{':'.join(str(arg) for arg in args)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_session_cache(self, session_id: str) -> LRUCache:
        """Get or create session-specific cache."""
        if session_id not in self.session_caches:
            self.session_caches[session_id] = LRUCache(max_size=100, max_memory_mb=10)
        return self.session_caches[session_id]
    
    def get(self, cache_type: str, *args) -> Optional[Any]:
        """Get value from multi-level cache."""
        key = self._generate_key(cache_type, *args)
        
        # Try L1 cache first
        value = self.l1_cache.get(key)
        if value is not None:
            return value
        
        # Try L2 cache (file-based)
        value = self._get_from_l2_cache(key)
        if value is not None:
            # Promote to L1 cache
            ttl = self.ttl_configs.get(cache_type, 3600)
            self.l1_cache.set(key, value, ttl)
            return value
        
        return None
    
    def set(self, cache_type: str, value: Any, *args) -> None:
        """Set value in multi-level cache."""
        key = self._generate_key(cache_type, *args)
        ttl = self.ttl_configs.get(cache_type, 3600)
        
        # Set in L1 cache
        self.l1_cache.set(key, value, ttl)
        
        # Set in L2 cache for persistence
        self._set_in_l2_cache(key, value, ttl)
    
    def get_session(self, session_id: str, cache_type: str, *args) -> Optional[Any]:
        """Get value from session-specific cache."""
        session_cache = self._get_session_cache(session_id)
        key = self._generate_key(cache_type, *args)
        return session_cache.get(key)
    
    def set_session(self, session_id: str, cache_type: str, value: Any, *args) -> None:
        """Set value in session-specific cache."""
        session_cache = self._get_session_cache(session_id)
        key = self._generate_key(cache_type, *args)
        ttl = self.ttl_configs.get(cache_type, 3600)
        session_cache.set(key, value, ttl)
    
    def _get_from_l2_cache(self, key: str) -> Optional[Any]:
        """Get value from L2 file cache."""
        cache_file = self.l2_cache_dir / f"{key}.pkl"
        
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            
            # Check if expired
            if time.time() - data['created_at'] > data['ttl']:
                cache_file.unlink()
                return None
            
            return data['value']
        except:
            # Remove corrupted file
            cache_file.unlink(missing_ok=True)
            return None
    
    def _set_in_l2_cache(self, key: str, value: Any, ttl: float) -> None:
        """Set value in L2 file cache."""
        cache_file = self.l2_cache_dir / f"{key}.pkl"
        
        try:
            data = {
                'value': value,
                'created_at': time.time(),
                'ttl': ttl
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
        except:
            pass  # Ignore cache write errors
    
    def delete(self, cache_type: str, *args) -> bool:
        """Delete value from cache."""
        key = self._generate_key(cache_type, *args)
        
        # Delete from L1
        l1_deleted = self.l1_cache.delete(key)
        
        # Delete from L2
        cache_file = self.l2_cache_dir / f"{key}.pkl"
        l2_deleted = cache_file.exists()
        if l2_deleted:
            cache_file.unlink()
        
        return l1_deleted or l2_deleted
    
    def clear_session(self, session_id: str) -> None:
        """Clear session-specific cache."""
        if session_id in self.session_caches:
            self.session_caches[session_id].clear()
            del self.session_caches[session_id]
    
    def start_cleanup_task(self):
        """Start background cleanup task."""
        if not self._cleanup_started:
            try:
                loop = asyncio.get_running_loop()
                if self.cleanup_task is None or self.cleanup_task.done():
                    self.cleanup_task = asyncio.create_task(self._cleanup_loop())
                    self._cleanup_started = True
            except RuntimeError:
                # No event loop running, will start later
                pass
    
    async def _cleanup_loop(self):
        """Background cleanup loop."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Cache cleanup error: {e}")
    
    def _cleanup_expired(self):
        """Clean up expired cache entries."""
        # Clean L1 cache (handled by LRU cache)
        
        # Clean L2 cache files
        current_time = time.time()
        for cache_file in self.l2_cache_dir.glob("*.pkl"):
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                
                if current_time - data['created_at'] > data['ttl']:
                    cache_file.unlink()
            except:
                cache_file.unlink(missing_ok=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        l1_stats = self.l1_cache.stats()
        
        # Count L2 cache files
        l2_files = len(list(self.l2_cache_dir.glob("*.pkl")))
        
        return {
            "l1_cache": l1_stats,
            "l2_cache_files": l2_files,
            "active_sessions": len(self.session_caches),
            "cache_types": list(self.ttl_configs.keys())
        }
    
    async def ensure_cleanup_task(self):
        """Ensure cleanup task is running (call this from FastAPI startup)."""
        if not self._cleanup_started:
            try:
                self.cleanup_task = asyncio.create_task(self._cleanup_loop())
                self._cleanup_started = True
                print("🔧 Advanced cache cleanup task started")
            except Exception as e:
                print(f"⚠️ Failed to start cache cleanup task: {e}")


# Global cache instance
advanced_cache = AdvancedCache()
