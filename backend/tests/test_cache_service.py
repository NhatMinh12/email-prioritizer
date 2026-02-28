"""Tests for the Redis cache service."""

import json
import uuid
from unittest.mock import MagicMock, PropertyMock

import pytest
import redis

from app.services.cache_service import CacheService


class TestMakeCacheKey:
    """Tests for deterministic cache key generation."""

    def test_same_input_produces_same_key(self):
        user_id = uuid.uuid4()
        key1 = CacheService.make_cache_key(user_id, "a@b.com", "Hi", "body")
        key2 = CacheService.make_cache_key(user_id, "a@b.com", "Hi", "body")
        assert key1 == key2

    def test_different_user_produces_different_key(self):
        key1 = CacheService.make_cache_key(uuid.uuid4(), "a@b.com", "Hi", "body")
        key2 = CacheService.make_cache_key(uuid.uuid4(), "a@b.com", "Hi", "body")
        assert key1 != key2

    def test_different_subject_produces_different_key(self):
        user_id = uuid.uuid4()
        key1 = CacheService.make_cache_key(user_id, "a@b.com", "Hi", "body")
        key2 = CacheService.make_cache_key(user_id, "a@b.com", "Hello", "body")
        assert key1 != key2

    def test_none_body_preview_handled(self):
        user_id = uuid.uuid4()
        key = CacheService.make_cache_key(user_id, "a@b.com", "Hi", None)
        assert key.startswith("classification:")

    def test_unicode_content_handled(self):
        user_id = uuid.uuid4()
        key = CacheService.make_cache_key(
            user_id, "user@example.com", "日本語の件名", "Ünïcödé bödy"
        )
        assert key.startswith("classification:")

    def test_key_is_prefixed(self):
        user_id = uuid.uuid4()
        key = CacheService.make_cache_key(user_id, "a@b.com", "Hi", "body")
        assert key.startswith("classification:")
        # SHA-256 hex = 64 chars
        assert len(key) == len("classification:") + 64


class TestCacheGet:
    """Tests for cache retrieval."""

    def test_get_returns_none_on_miss(self, cache_service):
        result = cache_service.get("classification:nonexistent")
        assert result is None

    def test_get_returns_parsed_dict_on_hit(self, cache_service, fake_redis_client):
        data = {"priority": "high", "urgency": "urgent", "needs_response": True}
        fake_redis_client.set("classification:testkey", json.dumps(data))
        result = cache_service.get("classification:testkey")
        assert result == data

    def test_get_returns_none_on_redis_error(self):
        mock_redis = MagicMock(spec=redis.Redis)
        mock_redis.get.side_effect = redis.RedisError("Connection refused")
        service = CacheService(redis_client=mock_redis)
        result = service.get("some_key")
        assert result is None

    def test_get_returns_none_on_invalid_json(self, fake_redis_client):
        fake_redis_client.set("classification:badkey", b"not-json{{{")
        service = CacheService(redis_client=fake_redis_client)
        result = service.get("classification:badkey")
        assert result is None


class TestCacheSet:
    """Tests for cache storage."""

    def test_set_stores_json_with_ttl(self, cache_service, fake_redis_client):
        data = {"priority": "low", "reason": "test"}
        cache_service.set("classification:mykey", data)
        stored = fake_redis_client.get("classification:mykey")
        assert json.loads(stored) == data
        ttl = fake_redis_client.ttl("classification:mykey")
        assert ttl > 0

    def test_set_silently_handles_redis_error(self):
        mock_redis = MagicMock(spec=redis.Redis)
        mock_redis.set.side_effect = redis.RedisError("Connection refused")
        service = CacheService(redis_client=mock_redis)
        # Should not raise
        service.set("some_key", {"data": "value"})


class TestCacheDelete:
    """Tests for cache deletion."""

    def test_delete_removes_key(self, cache_service, fake_redis_client):
        fake_redis_client.set("classification:delme", b"value")
        cache_service.delete("classification:delme")
        assert fake_redis_client.get("classification:delme") is None

    def test_delete_silently_handles_redis_error(self):
        mock_redis = MagicMock(spec=redis.Redis)
        mock_redis.delete.side_effect = redis.RedisError("Connection refused")
        service = CacheService(redis_client=mock_redis)
        service.delete("some_key")


class TestCachePing:
    """Tests for health check."""

    def test_ping_returns_true_when_healthy(self, cache_service):
        assert cache_service.ping() is True

    def test_ping_returns_false_on_error(self):
        mock_redis = MagicMock(spec=redis.Redis)
        mock_redis.ping.side_effect = redis.RedisError("Connection refused")
        service = CacheService(redis_client=mock_redis)
        assert service.ping() is False
