"""Unit tests for JWT utility functions."""

import time

import pytest

from app.utils.jwt import create_access_token, decode_access_token


def test_create_and_decode_token():
    """A token created for a user should decode back to the same claims."""
    token = create_access_token(user_id="test-uuid", email="user@example.com")
    payload = decode_access_token(token)

    assert payload.sub == "test-uuid"
    assert payload.email == "user@example.com"
    assert payload.exp > int(time.time())  # expiry must be in the future


def test_invalid_token_raises_value_error():
    """Garbage input must raise ValueError, not crash with an unhandled exception."""
    with pytest.raises(ValueError, match="Invalid or expired token"):
        decode_access_token("this.is.not.a.valid.jwt")


def test_tampered_token_raises_value_error():
    """A token with a modified payload must be rejected."""
    token = create_access_token(user_id="user-1", email="a@b.com")
    # Flip one character in the signature segment
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(ValueError):
        decode_access_token(tampered)

