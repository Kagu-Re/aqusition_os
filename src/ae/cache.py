"""Caching layer for frequently accessed data.

Provides Redis-backed caching with in-memory fallback for single instance deployments.
"""

from __future__ import annotations

import os
import json
import time
from typing import Optional, Dict, Any, TypeVar, Callable
from threading import Lock
from functools import wraps

T = TypeVar('T')

# Optional Redis support
try:
    import redis.asyncio as redis_async  # type: ignore
except Exception:
    redis_async = None


def _env_int(key: str, default: int) -> int:
    v = os.getenv(key)
    if v is None or v.strip() == "":
        return default
    return int(v.strip())


class CacheManager:
    """Manages caching for frequently accessed data.
    
    Uses Redis if available for multi-instance deployments, otherwise falls back to in-memory cache.
    """
    
    def __init__(self):
        self.redis_url = (os.getenv("AE_REDIS_URL") or "").strip()
        self.redis_prefix = (os.getenv("AE_REDIS_PREFIX") or "ae").strip()
        self._redis: Optional[redis_async.Redis] = None
        self._redis_initialized = False
        
        # In-memory cache
        self._cache: Dict[str, tuple[Any, float]] = {}  # key -> (value, expiry_time)
        self._cache_lock = Lock()
        
        # Initialize Redis if available
        if self.redis_url and redis_async:
            try:
                self._redis = redis_async.from_url(self.redis_url, decode_responses=True)
                self._redis_initialized = True
            except Exception:
                # Redis connection failed, use in-memory fallback
                self._redis = None
                self._redis_initialized = False
    
    def _use_redis(self) -> bool:
        """Check if Redis should be used."""
        return self._redis_initialized and self._redis is not None
    
    def _cleanup_memory_cache(self):
        """Remove expired entries from in-memory cache."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items()
            if expiry < current_time
        ]
        for key in expired_keys:
            del self._cache[key]
    
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        cache_key = f"{self.redis_prefix}:cache:{key}"
        
        if self._use_redis():
            try:
                value = await self._redis.get(cache_key)
                if value:
                    return json.loads(value)
                return None
            except Exception:
                # Fallback to memory on Redis error
                pass
        
        with self._cache_lock:
            self._cleanup_memory_cache()
            if key in self._cache:
                value, expiry = self._cache[key]
                if expiry > time.time():
                    return value
                else:
                    del self._cache[key]
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Set a value in cache with TTL."""
        cache_key = f"{self.redis_prefix}:cache:{key}"
        
        if self._use_redis():
            try:
                await self._redis.setex(cache_key, ttl_seconds, json.dumps(value))
                return
            except Exception:
                # Fallback to memory on Redis error
                pass
        
        with self._cache_lock:
            self._cleanup_memory_cache()
            expiry_time = time.time() + ttl_seconds
            self._cache[key] = (value, expiry_time)
    
    async def delete(self, key: str) -> None:
        """Delete a value from cache."""
        cache_key = f"{self.redis_prefix}:cache:{key}"
        
        if self._use_redis():
            try:
                await self._redis.delete(cache_key)
                return
            except Exception:
                pass
        
        with self._cache_lock:
            if key in self._cache:
                del self._cache[key]
    
    async def clear_pattern(self, pattern: str) -> None:
        """Clear cache entries matching a pattern (Redis only, approximate for memory)."""
        if self._use_redis():
            try:
                # Note: Redis SCAN would be needed for pattern deletion
                # For simplicity, we'll let TTL handle cleanup
                return
            except Exception:
                pass
        
        # For in-memory, we can't easily do pattern matching
        # Just clear matching keys (or implement a more sophisticated approach)
        with self._cache_lock:
            keys_to_delete = [k for k in self._cache.keys() if pattern in k]
            for k in keys_to_delete:
                del self._cache[k]


# Global singleton instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """Decorator to cache function results.
    
    Args:
        ttl_seconds: Time to live for cached values
        key_prefix: Optional prefix for cache keys
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            cache_mgr = get_cache_manager()
            
            # Generate cache key from function name and arguments
            cache_key_parts = [key_prefix, func.__name__]
            if args:
                cache_key_parts.append(str(hash(args)))
            if kwargs:
                cache_key_parts.append(str(hash(tuple(sorted(kwargs.items())))))
            cache_key = ":".join(filter(None, cache_key_parts))
            
            # Try to get from cache
            cached_value = await cache_mgr.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache_mgr.set(cache_key, result, ttl_seconds)
            return result
        
        return wrapper
    return decorator
