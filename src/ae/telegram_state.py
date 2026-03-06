"""Distributed state management for Telegram bot.

Provides Redis-backed state management with in-memory fallback for single instance deployments.
"""

from __future__ import annotations

import os
import time
from typing import Optional, Set, Dict
from threading import Lock
from collections import deque

# Optional Redis support
try:
    import redis.asyncio as redis_async  # type: ignore
except Exception:
    redis_async = None


def _env_bool(key: str, default: bool) -> bool:
    v = os.getenv(key)
    if v is None or v.strip() == "":
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


class TelegramStateManager:
    """Manages distributed state for Telegram bot operations.
    
    Uses Redis if available for multi-instance deployments, otherwise falls back to in-memory state.
    """
    
    def __init__(self):
        self.redis_url = (os.getenv("AE_REDIS_URL") or "").strip()
        self.redis_prefix = (os.getenv("AE_REDIS_PREFIX") or "ae").strip()
        self._redis: Optional[redis_async.Redis] = None
        self._redis_initialized = False
        
        # In-memory fallback state
        # P1 FIX: Use deque for deterministic FIFO ordering instead of set
        self._processed_message_ids: deque = deque(maxlen=1000)  # Max 1000 entries, auto-evicts oldest
        self._processed_message_ids_set: Set[str] = set()  # Fast lookup set
        self._start_command_cooldown: Dict[str, float] = {}
        self._processed_deep_links: Dict[str, float] = {}
        self._booking_creation_cooldown: Dict[str, float] = {}
        self._active_start_processing: Set[str] = set()
        self._memory_lock = Lock()
        
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
    
    # Processed message IDs
    
    async def is_message_processed(self, message_key: str) -> bool:
        """Check if a message has been processed."""
        if self._use_redis():
            try:
                key = f"{self.redis_prefix}:tg:msg:{message_key}"
                exists = await self._redis.exists(key)
                return exists == 1
            except Exception:
                # Fallback to memory on Redis error
                pass
        
        with self._memory_lock:
            return message_key in self._processed_message_ids_set
    
    async def mark_message_processed(self, message_key: str, ttl_seconds: int = 3600) -> None:
        """Mark a message as processed."""
        if self._use_redis():
            try:
                key = f"{self.redis_prefix}:tg:msg:{message_key}"
                await self._redis.setex(key, ttl_seconds, "1")
                return
            except Exception:
                # Fallback to memory on Redis error
                pass
        
        with self._memory_lock:
            # P1 FIX: Use deque for deterministic FIFO eviction
            if message_key not in self._processed_message_ids_set:
                # Add to deque (auto-evicts oldest if at maxlen)
                if len(self._processed_message_ids) >= 1000:
                    # Remove oldest from set when deque auto-evicts
                    oldest = self._processed_message_ids[0] if self._processed_message_ids else None
                    if oldest:
                        self._processed_message_ids_set.discard(oldest)
                self._processed_message_ids.append(message_key)
                self._processed_message_ids_set.add(message_key)
    
    # Start command cooldown
    
    async def get_start_cooldown(self, chat_id: str) -> float:
        """Get the last start command time for a chat_id."""
        if self._use_redis():
            try:
                key = f"{self.redis_prefix}:tg:start_cooldown:{chat_id}"
                value = await self._redis.get(key)
                if value:
                    return float(value)
                return 0.0
            except Exception:
                pass
        
        with self._memory_lock:
            return self._start_command_cooldown.get(chat_id, 0.0)
    
    async def set_start_cooldown(self, chat_id: str, timestamp: float, ttl_seconds: int = 30) -> None:
        """Set the start command cooldown timestamp."""
        if self._use_redis():
            try:
                key = f"{self.redis_prefix}:tg:start_cooldown:{chat_id}"
                await self._redis.setex(key, ttl_seconds, str(timestamp))
                return
            except Exception:
                pass
        
        with self._memory_lock:
            self._start_command_cooldown[chat_id] = timestamp
            # Clean up old entries
            if len(self._start_command_cooldown) > 1000:
                cutoff_time = timestamp - 30.0
                self._start_command_cooldown = {
                    cid: ts for cid, ts in self._start_command_cooldown.items()
                    if ts > cutoff_time
                }
    
    # Processed deep links
    
    async def get_deep_link_time(self, deep_link_key: str) -> float:
        """Get the last processed time for a deep link."""
        if self._use_redis():
            try:
                key = f"{self.redis_prefix}:tg:deep_link:{deep_link_key}"
                value = await self._redis.get(key)
                if value:
                    return float(value)
                return 0.0
            except Exception:
                pass
        
        with self._memory_lock:
            return self._processed_deep_links.get(deep_link_key, 0.0)
    
    async def set_deep_link_time(self, deep_link_key: str, timestamp: float, ttl_seconds: int = 30) -> None:
        """Set the processed time for a deep link."""
        if self._use_redis():
            try:
                key = f"{self.redis_prefix}:tg:deep_link:{deep_link_key}"
                await self._redis.setex(key, ttl_seconds, str(timestamp))
                return
            except Exception:
                pass
        
        with self._memory_lock:
            self._processed_deep_links[deep_link_key] = timestamp
            # Clean up old entries
            if len(self._processed_deep_links) > 1000:
                cutoff_time = timestamp - 30.0
                self._processed_deep_links = {
                    key: ts for key, ts in self._processed_deep_links.items()
                    if ts > cutoff_time
                }
    
    # Booking creation cooldown
    
    async def get_booking_cooldown(self, chat_id: str) -> float:
        """Get the last booking creation time for a chat_id."""
        if self._use_redis():
            try:
                key = f"{self.redis_prefix}:tg:booking_cooldown:{chat_id}"
                value = await self._redis.get(key)
                if value:
                    return float(value)
                return 0.0
            except Exception:
                pass
        
        with self._memory_lock:
            return self._booking_creation_cooldown.get(chat_id, 0.0)
    
    async def set_booking_cooldown(self, chat_id: str, timestamp: float, ttl_seconds: int = 60) -> None:
        """Set the booking creation cooldown timestamp."""
        if self._use_redis():
            try:
                key = f"{self.redis_prefix}:tg:booking_cooldown:{chat_id}"
                await self._redis.setex(key, ttl_seconds, str(timestamp))
                return
            except Exception:
                pass
        
        with self._memory_lock:
            self._booking_creation_cooldown[chat_id] = timestamp
    
    # Active start processing lock
    
    async def try_acquire_start_lock(self, chat_id: str, timeout_seconds: int = 30) -> bool:
        """Try to acquire a distributed lock for processing /start command.
        
        Returns True if lock was acquired, False if already locked.
        """
        if self._use_redis():
            try:
                key = f"{self.redis_prefix}:tg:start_lock:{chat_id}"
                # Use SET NX EX for atomic lock acquisition
                acquired = await self._redis.set(key, "1", nx=True, ex=timeout_seconds)
                return bool(acquired)
            except Exception:
                # Fallback to memory on Redis error
                pass
        
        with self._memory_lock:
            if chat_id in self._active_start_processing:
                return False
            self._active_start_processing.add(chat_id)
            return True
    
    async def release_start_lock(self, chat_id: str) -> None:
        """Release the distributed lock for processing /start command."""
        if self._use_redis():
            try:
                key = f"{self.redis_prefix}:tg:start_lock:{chat_id}"
                await self._redis.delete(key)
                return
            except Exception:
                pass
        
        with self._memory_lock:
            self._active_start_processing.discard(chat_id)
    
    async def clear_start_locks(self) -> None:
        """Clear all start locks (useful for cleanup on startup)."""
        if self._use_redis():
            try:
                # Note: This is a simple implementation. In production, you might want
                # to track lock keys or use a pattern-based delete
                pattern = f"{self.redis_prefix}:tg:start_lock:*"
                # Redis doesn't have a direct pattern delete, so we'd need to scan
                # For now, we'll just let TTL handle cleanup
                return
            except Exception:
                pass
        
        with self._memory_lock:
            self._active_start_processing.clear()
    
    async def clear_all_locks(self) -> None:
        """Clear all locks and reset state (for clean local dev startup)."""
        if self._use_redis():
            try:
                # Clear all Telegram-related keys with pattern matching
                # Note: Redis SCAN would be needed for production, but for local dev
                # we can rely on TTL expiration
                pass
            except Exception:
                pass
        
        with self._memory_lock:
            # Clear all in-memory locks and state
            self._active_start_processing.clear()
            # Clear processed message IDs for clean local dev startup
            # This prevents old messages from being blocked by deduplication
            self._processed_message_ids.clear()
            self._processed_message_ids_set.clear()
            # Note: We don't clear cooldowns/deep links as they're time-based and will expire naturally


# Global singleton instance
_state_manager: Optional[TelegramStateManager] = None


def get_state_manager() -> TelegramStateManager:
    """Get the global Telegram state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = TelegramStateManager()
    return _state_manager
