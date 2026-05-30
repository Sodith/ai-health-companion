"""Unit tests for password utility functions."""

from app.utils.password import hash_password, verify_password


def test_hash_is_not_plain_text():
    """Hashed password must never equal the original."""
    hashed = hash_password("MyPass@123")
    assert hashed != "MyPass@123"


def test_verify_correct_password():
    """verify_password returns True for the correct plain password."""
    hashed = hash_password("MyPass@123")
    assert verify_password("MyPass@123", hashed) is True


def test_verify_wrong_password():
    """verify_password returns False for a wrong password."""
    hashed = hash_password("MyPass@123")
    assert verify_password("WrongPass@456", hashed) is False


def test_two_hashes_of_same_password_differ():
    """Each hash call should produce a different salt — never store identical hashes."""
    hash1 = hash_password("MyPass@123")
    hash2 = hash_password("MyPass@123")
    assert hash1 != hash2

