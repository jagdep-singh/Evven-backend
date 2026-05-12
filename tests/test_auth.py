from datetime import timedelta

from services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
    password_hashing,
    verify_password,
)


def test_1_password_is_hashed():
    """Hash differs from plaintext."""
    assert password_hashing("Jazz@123") != "Jazz@123"


def test_2_correct_password_verifies():
    """Correct password passes verification."""
    hashed = password_hashing("Jazz@123")
    assert verify_password("Jazz@123", hashed) is True


def test_3_wrong_password_fails():
    """Wrong password fails verification."""
    hashed = password_hashing("Jazz@123")
    assert verify_password("WrongPass!", hashed) is False


def test_4_same_password_produces_different_hashes():
    """bcrypt salts mean two hashes of the same password differ."""
    h1 = password_hashing("Jazz@123")
    h2 = password_hashing("Jazz@123")
    assert h1 != h2


def test_5_access_token_roundtrip():
    """Encoded payload survives encode → decode."""
    token = create_access_token({"sub": "user-123"})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"


def test_6_access_token_has_exp():
    """Token carries an expiry claim."""
    token = create_access_token({"sub": "user-123"})
    payload = decode_token(token)
    assert "exp" in payload


def test_7_expired_access_token_returns_none():
    """Token expired in the past decodes to None."""
    token = create_access_token(
        {"sub": "user-123"}, expires_delta=timedelta(seconds=-1)
    )
    assert decode_token(token) is None


def test_8_tampered_token_returns_none():
    """Corrupted token decodes to None."""
    token = create_access_token({"sub": "user-123"})
    assert decode_token(token + "tampered") is None


def test_9_garbage_string_returns_none():
    """Completely invalid string decodes to None."""
    assert decode_token("not.a.token") is None


def test_10_refresh_token_roundtrip():
    """Refresh token payload survives encode → decode."""
    token = create_refresh_token({"sub": "user-456"})
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-456"


def test_11_refresh_token_has_exp():
    """Refresh token carries an expiry claim."""
    token = create_refresh_token({"sub": "user-456"})
    payload = decode_token(token)
    assert "exp" in payload


def test_12_expired_refresh_token_returns_none():
    """Expired refresh token decodes to None."""
    token = create_refresh_token(
        {"sub": "user-456"}, expires_delta=timedelta(seconds=-1)
    )
    assert decode_token(token) is None


def test_13_access_and_refresh_tokens_differ():
    """Access and refresh tokens for same payload are not identical."""
    payload = {"sub": "user-789"}
    access = create_access_token(payload)
    refresh = create_refresh_token(payload)
    assert access != refresh


def test_14_access_token_fails_refresh_validation():
    access_token = create_access_token({"sub": "user-123"})

    payload = decode_token(
        access_token,
        expected_type="refresh",
    )

    assert payload is None
