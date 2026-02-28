"""Redis cache service for email classification results.

Gracefully degrades: if Redis is unavailable, all operations
return None / silently skip, so the system continues without cache.
"""

import hashlib
import json
import logging
import uuid
from typing import Optional

import redis

from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Manages Redis caching for email classification results."""

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client
        self._ttl = settings.cache_ttl

    @staticmethod
    def make_cache_key(
        user_id: uuid.UUID,
        sender: str,
        subject: str,
        body_preview: Optional[str],
    ) -> str:
        """Generate a deterministic cache key from email content.

        Uses SHA-256 of (user_id + sender + subject + body_preview).
        Scoped to user to avoid cross-user data leakage.
        """
        content = f"{user_id}:{sender}:{subject}:{body_preview or ''}"
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return f"classification:{content_hash}"

    def get(self, cache_key: str) -> Optional[dict]:
        """Retrieve a cached classification result.

        Returns parsed dict or None on miss/error.
        """
        try:
            raw = self._redis.get(cache_key)
            if raw is None:
                return None
            return json.loads(raw)
        except redis.RedisError as exc:
            logger.warning("Redis GET failed (key=%s): %s", cache_key, exc)
            return None
        except json.JSONDecodeError as exc:
            logger.warning("Cache value is not valid JSON (key=%s): %s", cache_key, exc)
            return None

    def set(self, cache_key: str, value: dict) -> None:
        """Store a classification result in cache with TTL."""
        try:
            self._redis.set(cache_key, json.dumps(value), ex=self._ttl)
        except redis.RedisError as exc:
            logger.warning("Redis SET failed (key=%s): %s", cache_key, exc)

    def delete(self, cache_key: str) -> None:
        """Remove a cached result."""
        try:
            self._redis.delete(cache_key)
        except redis.RedisError as exc:
            logger.warning("Redis DELETE failed (key=%s): %s", cache_key, exc)

    def ping(self) -> bool:
        """Health check for Redis connectivity."""
        try:
            return self._redis.ping()
        except redis.RedisError:
            return False
