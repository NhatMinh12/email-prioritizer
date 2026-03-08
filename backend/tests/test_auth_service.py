"""Tests for JWT authentication service."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from jose import jwt, JWTError

from app.config import settings
from app.services.auth_service import create_access_token, verify_access_token


@pytest.fixture()
def user_id():
    return uuid.uuid4()


@pytest.fixture()
def user_email():
    return "test@example.com"


class TestCreateAccessToken:
    def test_returns_string(self, user_id, user_email):
        token = create_access_token(user_id, user_email)
        assert isinstance(token, str)

    def test_token_contains_expected_claims(self, user_id, user_email):
        token = create_access_token(user_id, user_email)
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        assert payload["sub"] == str(user_id)
        assert payload["email"] == user_email
        assert "exp" in payload

    def test_token_expiry_is_in_future(self, user_id, user_email):
        token = create_access_token(user_id, user_email)
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp > datetime.now(timezone.utc)

    def test_token_expiry_matches_settings(self, user_id, user_email):
        before = datetime.now(timezone.utc)
        token = create_access_token(user_id, user_email)
        after = datetime.now(timezone.utc)

        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)

        assert exp >= before + expected_delta - timedelta(seconds=1)
        assert exp <= after + expected_delta + timedelta(seconds=1)

    def test_different_users_get_different_tokens(self, user_email):
        token_a = create_access_token(uuid.uuid4(), user_email)
        token_b = create_access_token(uuid.uuid4(), user_email)
        assert token_a != token_b


class TestVerifyAccessToken:
    def test_valid_token_returns_payload(self, user_id, user_email):
        token = create_access_token(user_id, user_email)
        payload = verify_access_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["email"] == user_email

    def test_expired_token_raises(self, user_id, user_email):
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {"sub": str(user_id), "email": user_email, "exp": expire}
        token = jwt.encode(
            payload, settings.secret_key, algorithm=settings.jwt_algorithm
        )
        with pytest.raises(JWTError):
            verify_access_token(token)

    def test_invalid_token_raises(self):
        with pytest.raises(JWTError):
            verify_access_token("not.a.valid.token")

    def test_wrong_secret_raises(self, user_id, user_email):
        payload = {
            "sub": str(user_id),
            "email": user_email,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, "wrong_secret", algorithm=settings.jwt_algorithm)
        with pytest.raises(JWTError):
            verify_access_token(token)

    def test_missing_sub_claim_raises(self, user_email):
        payload = {
            "email": user_email,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(
            payload, settings.secret_key, algorithm=settings.jwt_algorithm
        )
        with pytest.raises(JWTError, match="missing required claims"):
            verify_access_token(token)

    def test_missing_email_claim_raises(self, user_id):
        payload = {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(
            payload, settings.secret_key, algorithm=settings.jwt_algorithm
        )
        with pytest.raises(JWTError, match="missing required claims"):
            verify_access_token(token)

    def test_tampered_token_raises(self, user_id, user_email):
        token = create_access_token(user_id, user_email)
        # Tamper with the token by modifying a character in the signature
        parts = token.split(".")
        sig = parts[2]
        tampered_char = "A" if sig[0] != "A" else "B"
        parts[2] = tampered_char + sig[1:]
        tampered_token = ".".join(parts)
        with pytest.raises(JWTError):
            verify_access_token(tampered_token)
