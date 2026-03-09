"""Tests for authentication API routes."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.models import User
from app.services.auth_service import create_access_token
from app.services.oauth_service import OAuthError, OAuthTokens


class TestLoginEndpoint:
    def test_login_returns_authorization_url(self, client: TestClient):
        response = client.get("/auth/login")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "accounts.google.com" in data["authorization_url"]

    def test_login_url_contains_client_id(self, client: TestClient):
        response = client.get("/auth/login")
        data = response.json()
        assert "client_id=" in data["authorization_url"]

    def test_login_url_contains_gmail_scope(self, client: TestClient):
        response = client.get("/auth/login")
        data = response.json()
        assert "gmail.readonly" in data["authorization_url"]

    def test_login_url_contains_openid_scope(self, client: TestClient):
        response = client.get("/auth/login")
        data = response.json()
        url = data["authorization_url"]
        assert "openid" in url
        assert "email" in url

    def test_login_url_contains_prompt_consent(self, client: TestClient):
        response = client.get("/auth/login")
        data = response.json()
        assert "prompt=consent" in data["authorization_url"]

    def test_login_url_contains_offline_access(self, client: TestClient):
        response = client.get("/auth/login")
        data = response.json()
        assert "access_type=offline" in data["authorization_url"]


class TestCallbackEndpoint:
    @patch("app.api.auth.exchange_code_for_tokens")
    def test_callback_creates_user_and_returns_jwt(
        self, mock_exchange, client: TestClient
    ):
        mock_exchange.return_value = OAuthTokens(
            access_token="access_123",
            refresh_token="refresh_456",
            expiry=datetime(2026, 4, 1, tzinfo=timezone.utc),
            email="new@example.com",
        )

        response = client.get("/auth/callback", params={"code": "test_code"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @patch("app.api.auth.exchange_code_for_tokens")
    def test_callback_with_existing_user_updates_tokens(
        self, mock_exchange, client: TestClient, sample_user: User
    ):
        mock_exchange.return_value = OAuthTokens(
            access_token="new_access",
            refresh_token="new_refresh",
            expiry=datetime(2026, 5, 1, tzinfo=timezone.utc),
            email=sample_user.email,
        )

        response = client.get("/auth/callback", params={"code": "new_code"})

        assert response.status_code == 200
        assert "access_token" in response.json()

    @patch("app.api.auth.exchange_code_for_tokens")
    def test_callback_invalid_code_returns_400(
        self, mock_exchange, client: TestClient
    ):
        mock_exchange.side_effect = OAuthError("Invalid authorization code")

        response = client.get("/auth/callback", params={"code": "bad_code"})

        assert response.status_code == 400
        assert "Invalid" in response.json()["detail"]

    def test_callback_missing_code_returns_422(self, client: TestClient):
        response = client.get("/auth/callback")
        assert response.status_code == 422


class TestLogoutEndpoint:
    def test_logout_returns_200(self, client: TestClient):
        response = client.post("/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"


class TestMeEndpoint:
    def test_me_returns_current_user(
        self, authenticated_client: TestClient, sample_user: User
    ):
        response = authenticated_client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == sample_user.email
        assert data["id"] == str(sample_user.id)

    def test_me_without_token_returns_401(self, client: TestClient):
        response = client.get("/auth/me")
        assert response.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client: TestClient):
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    def test_me_with_expired_token_returns_401(self, client: TestClient):
        from jose import jwt
        from app.config import settings

        payload = {
            "sub": str(uuid.uuid4()),
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            payload, settings.secret_key, algorithm=settings.jwt_algorithm
        )
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_me_with_nonexistent_user_returns_401(self, client: TestClient):
        """Token valid but user not in DB."""
        token = create_access_token(uuid.uuid4(), "ghost@example.com")
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 401
