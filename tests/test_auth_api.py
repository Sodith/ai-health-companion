"""Integration tests for auth API endpoints.

These tests exercise the full request → controller → service → DB stack
using an in-memory SQLite database (see conftest.py).
"""

import pytest


SIGNUP_URL = "/api/v1/auth/signup"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"

VALID_PAYLOAD = {"email": "user@example.com", "password": "StrongPass@123"}


# ---------------------------------------------------------------------------
# POST /auth/signup
# ---------------------------------------------------------------------------

class TestSignup:
    def test_signup_success(self, client):
        """Valid payload creates a user and returns a token."""
        res = client.post(SIGNUP_URL, json=VALID_PAYLOAD)
        assert res.status_code == 201

        body = res.json()
        assert body["success"] is True
        assert body["data"]["access_token"] is not None
        assert body["data"]["user"]["email"] == VALID_PAYLOAD["email"]

    def test_signup_duplicate_email_returns_409(self, client):
        """Registering the same email twice must return 409."""
        client.post(SIGNUP_URL, json=VALID_PAYLOAD)
        res = client.post(SIGNUP_URL, json=VALID_PAYLOAD)
        assert res.status_code == 409

    def test_signup_weak_password_returns_422(self, client):
        """A password that fails complexity rules must return 422."""
        res = client.post(SIGNUP_URL, json={"email": "a@b.com", "password": "weak"})
        assert res.status_code == 422

    def test_signup_invalid_email_returns_422(self, client):
        """An invalid email address must return 422."""
        res = client.post(SIGNUP_URL, json={"email": "not-an-email", "password": "StrongPass@123"})
        assert res.status_code == 422


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_login_success(self, client):
        """Valid credentials return a 200 with a bearer token."""
        client.post(SIGNUP_URL, json=VALID_PAYLOAD)
        res = client.post(LOGIN_URL, json=VALID_PAYLOAD)

        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["data"]["access_token"] is not None
        assert body["data"]["token_type"] == "bearer"

    def test_login_wrong_password_returns_401(self, client):
        """Wrong password must return 401."""
        client.post(SIGNUP_URL, json=VALID_PAYLOAD)
        res = client.post(LOGIN_URL, json={"email": VALID_PAYLOAD["email"], "password": "WrongPass@999"})
        assert res.status_code == 401

    def test_login_unknown_email_returns_401(self, client):
        """Login with an email that was never registered must return 401."""
        res = client.post(LOGIN_URL, json={"email": "ghost@example.com", "password": "StrongPass@123"})
        assert res.status_code == 401


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

class TestGetMe:
    def _get_token(self, client) -> str:
        res = client.post(SIGNUP_URL, json=VALID_PAYLOAD)
        return res.json()["data"]["access_token"]

    def test_me_returns_current_user(self, client):
        """A valid bearer token returns the user's profile."""
        token = self._get_token(client)
        res = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})

        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["data"]["email"] == VALID_PAYLOAD["email"]

    def test_me_without_token_returns_401(self, client):
        """Missing Authorization header must return 401."""
        res = client.get(ME_URL)
        assert res.status_code == 401

    def test_me_with_invalid_token_returns_401(self, client):
        """A bogus token must return 401."""
        res = client.get(ME_URL, headers={"Authorization": "Bearer bad.token.here"})
        assert res.status_code == 401


