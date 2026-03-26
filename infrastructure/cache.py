"""
Production-Grade Caching System
Supports multiple backends and TTL-based expiration
"""

import json
import hashlib
from typing import Any, Optional, Callable, TypeVar, Dict
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
import pickle

T = TypeVar('T')


class CacheBackend:
    """Base class for cache backends"""

    def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache"""
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Store value in cache"""
        raise NotImplementedError

    def delete(self, key: str):
        """Delete value from cache"""
        raise NotImplementedError

    def clear(self):
        """Clear all cache"""
        raise NotImplementedError


class InMemoryCache(CacheBackend):
    """In-memory cache with TTL support"""

    def __init__(self, max_size: int = 1000):
        self.data: Dict[str, Any] = {}
        self.ttls: Dict[str, datetime] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        self._cleanup_expired()
        
        if key not in self.data:
            self.misses += 1
            return None
        
        # Check if expired
        if key in self.ttls and datetime.now() > self.ttls[key]:
            del self.data[key]
            del self.ttls[key]
            self.misses += 1
            return None
        
        self.hits += 1
        return self.data[key]

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set value with optional TTL"""
        # Simple LRU eviction if cache full
        if len(self.data) >= self.max_size and key not in self.data:
            oldest_key = next(iter(self.data))
            del self.data[oldest_key]
            if oldest_key in self.ttls:
                del self.ttls[oldest_key]
        
        self.data[key] = value
        
        if ttl_seconds:
            self.ttls[key] = datetime.now() + timedelta(seconds=ttl_seconds)

    def delete(self, key: str):
        """Delete value from cache"""
        self.data.pop(key, None)
        self.ttls.pop(key, None)

    def clear(self):
        """Clear all cache"""
        self.data.clear()
        self.ttls.clear()

    def _cleanup_expired(self):
        """Remove expired entries"""
        now = datetime.now()
        expired_keys = [
            k for k, exp_time in self.ttls.items()
            if now > exp_time
        ]
        for key in expired_keys:
            del self.data[key]
            del self.ttls[key]

    def get_stats(self) -> dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "size": len(self.data),
            "capacity": self.max_size
        }


class FileCache(CacheBackend):
    """File-based cache with TTL support"""

    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.ttls_file = self.cache_dir / ".ttls"
        self.ttls: Dict[str, datetime] = self._load_ttls()

    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key"""
        hashed = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hashed}.cache"

    def get(self, key: str) -> Optional[Any]:
        """Get value from file cache"""
        path = self._get_cache_path(key)
        
        if not path.exists():
            return None
        
        # Check TTL
        if key in self.ttls and datetime.now() > self.ttls[key]:
            path.unlink()
            del self.ttls[key]
            return None
        
        try:
            with open(path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set value in file cache"""
        path = self._get_cache_path(key)
        
        try:
            with open(path, 'wb') as f:
                pickle.dump(value, f)
            
            if ttl_seconds:
                self.ttls[key] = datetime.now() + timedelta(seconds=ttl_seconds)
                self._save_ttls()
        except Exception:
            pass

    def delete(self, key: str):
        """Delete value from cache"""
        path = self._get_cache_path(key)
        if path.exists():
            path.unlink()
        self.ttls.pop(key, None)
        self._save_ttls()

    def clear(self):
        """Clear all cache"""
        for file in self.cache_dir.glob("*.cache"):
            file.unlink()
        self.ttls.clear()
        self._save_ttls()

    def _load_ttls(self) -> Dict[str, datetime]:
        """Load TTL information"""
        if self.ttls_file.exists():
            try:
                with open(self.ttls_file, 'rb') as f:
                    ttls = pickle.load(f)
                    return ttls
            except Exception:
                pass
        return {}

    def _save_ttls(self):
        """Save TTL information"""
        try:
            with open(self.ttls_file, 'wb') as f:
                pickle.dump(self.ttls, f)
        except Exception:
            pass


class CacheManager:
    """Unified cache interface with multiple backends"""

    def __init__(self, backend: Optional[CacheBackend] = None):
        self.backend = backend or InMemoryCache()

    def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        return self.backend.get(key)

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """Set cached value"""
        self.backend.set(key, value, ttl_seconds)

    def delete(self, key: str):
        """Delete cached value"""
        self.backend.delete(key)

    def clear(self):
        """Clear all cache"""
        self.backend.clear()

    def memoize(self, ttl_seconds: Optional[int] = None):
        """
        Decorator for caching function results
        
        Usage:
            @cache.memoize(ttl_seconds=3600)
            def expensive_computation(x, y):
                return x + y
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args, **kwargs) -> T:
                # Create cache key from function name and arguments
                cache_key = f"{func.__name__}:{json.dumps(str((args, kwargs)))}"
                
                # Try to get from cache
                cached = self.get(cache_key)
                if cached is not None:
                    return cached
                
                # Compute and cache
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl_seconds)
                return result
            
            return wrapper
        return decorator


# Global cache instance
_cache_manager: Optional[CacheManager] = None


def init_cache(backend: Optional[CacheBackend] = None) -> CacheManager:
    """Initialize global cache"""
    global _cache_manager
    _cache_manager = CacheManager(backend)
    return _cache_manager


def get_cache() -> CacheManager:
    """Get global cache instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
