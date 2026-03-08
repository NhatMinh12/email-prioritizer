"""Tests for preferences API routes."""

import pytest
from fastapi.testclient import TestClient

from app.models import User, UserPreference


class TestGetPreferences:
    def test_get_preferences_returns_existing(
        self,
        authenticated_client: TestClient,
        sample_user_preference: UserPreference,
    ):
        response = authenticated_client.get("/api/preferences")
        assert response.status_code == 200
        data = response.json()
        assert data["important_senders"] == ["boss@company.com", "cto@company.com"]
        assert data["important_keywords"] == ["urgent", "deadline", "asap"]
        assert data["response_rate"] == 0.85

    def test_get_preferences_creates_defaults_if_none(
        self, authenticated_client: TestClient, sample_user: User
    ):
        response = authenticated_client.get("/api/preferences")
        assert response.status_code == 200
        data = response.json()
        assert data["important_senders"] == []
        assert data["important_keywords"] == []
        assert data["response_rate"] is None

    def test_get_preferences_requires_auth(self, client: TestClient):
        response = client.get("/api/preferences")
        assert response.status_code == 401


class TestUpdatePreferences:
    def test_partial_update_senders(
        self,
        authenticated_client: TestClient,
        sample_user_preference: UserPreference,
    ):
        response = authenticated_client.put(
            "/api/preferences",
            json={"important_senders": ["new-boss@company.com"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["important_senders"] == ["new-boss@company.com"]
        # Unchanged fields remain
        assert data["important_keywords"] == ["urgent", "deadline", "asap"]

    def test_partial_update_keywords(
        self,
        authenticated_client: TestClient,
        sample_user_preference: UserPreference,
    ):
        response = authenticated_client.put(
            "/api/preferences",
            json={"important_keywords": ["critical"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["important_keywords"] == ["critical"]
        assert data["important_senders"] == ["boss@company.com", "cto@company.com"]

    def test_full_update(
        self,
        authenticated_client: TestClient,
        sample_user_preference: UserPreference,
    ):
        response = authenticated_client.put(
            "/api/preferences",
            json={
                "important_senders": ["a@b.com"],
                "important_keywords": ["now"],
                "response_rate": 0.5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["important_senders"] == ["a@b.com"]
        assert data["important_keywords"] == ["now"]
        assert data["response_rate"] == 0.5

    def test_update_creates_preferences_if_none(
        self, authenticated_client: TestClient, sample_user: User
    ):
        response = authenticated_client.put(
            "/api/preferences",
            json={"important_senders": ["first@sender.com"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["important_senders"] == ["first@sender.com"]
        assert data["important_keywords"] == []

    def test_update_requires_auth(self, client: TestClient):
        response = client.put(
            "/api/preferences",
            json={"important_senders": ["a@b.com"]},
        )
        assert response.status_code == 401

    def test_empty_update_is_valid(
        self,
        authenticated_client: TestClient,
        sample_user_preference: UserPreference,
    ):
        """Sending {} with no fields should be a no-op."""
        response = authenticated_client.put("/api/preferences", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["important_senders"] == ["boss@company.com", "cto@company.com"]
