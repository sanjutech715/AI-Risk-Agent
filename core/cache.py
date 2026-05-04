"""
utils/cache.py
──────────────
Caching abstraction supporting Redis and in-memory backends.
"""

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional, Union

import redis.asyncio as redis

from config import settings

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache with optional TTL."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        pass


class RedisCache(CacheBackend):
    """Redis-based cache backend."""

    def __init__(self, url: str):
        self.redis = redis.from_url(url)

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache."""
        try:
            value = await self.redis.get(key)
            if value is None:
                return None
            return json.loads(value.decode('utf-8'))
        except Exception as e:
            logger.warning(f"Redis cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in Redis cache."""
        try:
            serialized = json.dumps(value)
            if ttl:
                await self.redis.setex(key, ttl, serialized)
            else:
                await self.redis.set(key, serialized)
        except Exception as e:
            logger.warning(f"Redis cache set error for key {key}: {e}")

    async def delete(self, key: str) -> None:
        """Delete value from Redis cache."""
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis cache delete error for key {key}: {e}")

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis cache."""
        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.warning(f"Redis cache exists error for key {key}: {e}")
            return False

    async def clear(self) -> None:
        """Clear all Redis cache entries."""
        try:
            await self.redis.flushdb()
        except Exception as e:
            logger.warning(f"Redis cache clear error: {e}")


class MemoryCache(CacheBackend):
    """In-memory cache backend for development/fallback."""

    def __init__(self):
        self._cache: dict[str, dict] = {}

    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory cache."""
        entry = self._cache.get(key)
        if entry is None:
            return None

        # Check TTL
        if entry.get('expires_at') and entry['expires_at'] < datetime.now().timestamp():
            await self.delete(key)
            return None

        return entry['value']

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in memory cache."""
        expires_at = None
        if ttl:
            expires_at = datetime.now().timestamp() + ttl

        self._cache[key] = {
            'value': value,
            'expires_at': expires_at
        }

    async def delete(self, key: str) -> None:
        """Delete value from memory cache."""
        self._cache.pop(key, None)

    async def exists(self, key: str) -> bool:
        """Check if key exists in memory cache."""
        entry = self._cache.get(key)
        if entry is None:
            return False

        # Check TTL
        if entry.get('expires_at') and entry['expires_at'] < datetime.now().timestamp():
            await self.delete(key)
            return False

        return True

    async def clear(self) -> None:
        """Clear all memory cache entries."""
        self._cache.clear()


# ── Cache Factory ─────────────────────────────────────────────────────────────
def create_cache() -> CacheBackend:
    """Create cache backend based on configuration."""
    if not settings.cache_enabled:
        return MemoryCache()  # Return memory cache as disabled placeholder

    try:
        return RedisCache(settings.redis_url)
    except Exception as e:
        logger.warning(f"Failed to connect to Redis at {settings.redis_url}: {e}")
        logger.info("Falling back to in-memory cache")
        return MemoryCache()


# ── Global cache instance ─────────────────────────────────────────────────────
cache = create_cache()