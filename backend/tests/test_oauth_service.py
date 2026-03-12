"""Tests for the OAuth service module."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from app.models import User
from app.services.oauth_service import (
    OAuthError,
    OAuthTokens,
    build_credentials,
    exchange_code_for_tokens,
    refresh_credentials_if_expired,
)


class TestExchangeCodeForTokens:
    @patch("app.services.oauth_service.Flow")
    def test_success(self, mock_flow_cls):
        """Successful code exchange returns OAuthTokens."""
        mock_flow = MagicMock()
        mock_flow_cls.from_client_config.return_value = mock_flow

        mock_creds = MagicMock()
        mock_creds.token = "access_123"
        mock_creds.refresh_token = "refresh_456"
        mock_creds.expiry = datetime(2026, 4, 1, tzinfo=timezone.utc)
        mock_creds.id_token = {"email": "user@example.com", "sub": "123"}
        mock_flow.credentials = mock_creds

        result = exchange_code_for_tokens("auth_code_abc")

        assert isinstance(result, OAuthTokens)
        assert result.access_token == "access_123"
        assert result.refresh_token == "refresh_456"
        assert result.email == "user@example.com"
        mock_flow.fetch_token.assert_called_once_with(code="auth_code_abc")

    @patch("app.services.oauth_service.Flow")
    def test_invalid_code_raises_oauth_error(self, mock_flow_cls):
        """Invalid authorization code raises OAuthError."""
        mock_flow = MagicMock()
        mock_flow_cls.from_client_config.return_value = mock_flow
        mock_flow.fetch_token.side_effect = Exception("invalid_grant")

        with pytest.raises(OAuthError, match="Failed to exchange"):
            exchange_code_for_tokens("bad_code")

    @patch("app.services.oauth_service.Flow")
    def test_no_refresh_token_raises_oauth_error(self, mock_flow_cls):
        """Missing refresh token raises OAuthError."""
        mock_flow = MagicMock()
        mock_flow_cls.from_client_config.return_value = mock_flow

        mock_creds = MagicMock()
        mock_creds.token = "access_123"
        mock_creds.refresh_token = None
        mock_flow.credentials = mock_creds

        with pytest.raises(OAuthError, match="No refresh token"):
            exchange_code_for_tokens("code_no_refresh")

    @patch("app.services.oauth_service.http_requests")
    @patch("app.services.oauth_service.Flow")
    def test_no_id_token_falls_back_to_userinfo(self, mock_flow_cls, mock_http):
        """Missing id_token falls back to userinfo endpoint."""
        mock_flow = MagicMock()
        mock_flow_cls.from_client_config.return_value = mock_flow

        mock_creds = MagicMock()
        mock_creds.token = "access_123"
        mock_creds.refresh_token = "refresh_456"
        mock_creds.expiry = datetime(2026, 4, 1, tzinfo=timezone.utc)
        mock_creds.id_token = None
        mock_flow.credentials = mock_creds

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"email": "fallback@example.com"}
        mock_http.get.return_value = mock_resp

        result = exchange_code_for_tokens("code_no_id")

        assert result.email == "fallback@example.com"
        mock_http.get.assert_called_once_with(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": "Bearer access_123"},
            timeout=10,
        )

    @patch("app.services.oauth_service.http_requests")
    @patch("app.services.oauth_service.Flow")
    def test_no_email_in_id_token_falls_back_to_userinfo(self, mock_flow_cls, mock_http):
        """id_token without email claim falls back to userinfo endpoint."""
        mock_flow = MagicMock()
        mock_flow_cls.from_client_config.return_value = mock_flow

        mock_creds = MagicMock()
        mock_creds.token = "access_123"
        mock_creds.refresh_token = "refresh_456"
        mock_creds.expiry = datetime(2026, 4, 1, tzinfo=timezone.utc)
        mock_creds.id_token = {"sub": "123"}  # no email
        mock_flow.credentials = mock_creds

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"email": "fallback@example.com"}
        mock_http.get.return_value = mock_resp

        result = exchange_code_for_tokens("code_no_email")

        assert result.email == "fallback@example.com"

    @patch("app.services.oauth_service.http_requests")
    @patch("app.services.oauth_service.Flow")
    def test_userinfo_fallback_failure_raises_oauth_error(self, mock_flow_cls, mock_http):
        """When both id_token and userinfo fail, raises OAuthError."""
        mock_flow = MagicMock()
        mock_flow_cls.from_client_config.return_value = mock_flow

        mock_creds = MagicMock()
        mock_creds.token = "access_123"
        mock_creds.refresh_token = "refresh_456"
        mock_creds.id_token = None
        mock_flow.credentials = mock_creds

        mock_http.get.side_effect = Exception("Network error")

        with pytest.raises(OAuthError, match="Failed to determine user email"):
            exchange_code_for_tokens("code_fail")


class TestBuildCredentials:
    def test_builds_credentials_from_user(self):
        """Builds a Credentials object from user's stored tokens."""
        user = MagicMock(spec=User)
        user.oauth_access_token = "access_token"
        user.oauth_refresh_token = "refresh_token"
        user.oauth_token_expiry = datetime(2026, 4, 1, tzinfo=timezone.utc)

        creds = build_credentials(user)

        assert isinstance(creds, Credentials)
        assert creds.token == "access_token"
        assert creds.refresh_token == "refresh_token"

    def test_no_refresh_token_raises_oauth_error(self):
        """User without refresh token raises OAuthError."""
        user = MagicMock(spec=User)
        user.oauth_refresh_token = None

        with pytest.raises(OAuthError, match="no OAuth credentials"):
            build_credentials(user)


class TestRefreshCredentialsIfExpired:
    def test_valid_credentials_not_refreshed(self):
        """Non-expired credentials are returned unchanged."""
        creds = MagicMock(spec=Credentials)
        creds.expired = False
        user = MagicMock(spec=User)
        db = MagicMock()

        result = refresh_credentials_if_expired(creds, user, db)

        assert result is creds
        creds.refresh.assert_not_called()
        db.commit.assert_not_called()

    @patch("app.services.oauth_service.Request")
    def test_expired_credentials_refreshed_and_persisted(self, mock_request_cls):
        """Expired credentials are refreshed and new tokens persisted to DB."""
        creds = MagicMock(spec=Credentials)
        creds.expired = True
        creds.token = "new_access_token"
        creds.expiry = datetime(2026, 5, 1, tzinfo=timezone.utc)

        user = MagicMock(spec=User)
        user.email = "test@example.com"
        db = MagicMock()

        result = refresh_credentials_if_expired(creds, user, db)

        assert result is creds
        creds.refresh.assert_called_once()
        assert user.oauth_access_token == "new_access_token"
        assert user.oauth_token_expiry == creds.expiry
        db.commit.assert_called_once()

    @patch("app.services.oauth_service.Request")
    def test_refresh_error_raises_oauth_error(self, mock_request_cls):
        """RefreshError (revoked token) raises OAuthError."""
        creds = MagicMock(spec=Credentials)
        creds.expired = True
        creds.refresh.side_effect = RefreshError("Token has been revoked")

        user = MagicMock(spec=User)
        user.email = "test@example.com"
        db = MagicMock()

        with pytest.raises(OAuthError, match="Re-authentication required"):
            refresh_credentials_if_expired(creds, user, db)

        db.commit.assert_not_called()
