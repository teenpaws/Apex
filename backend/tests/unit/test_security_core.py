"""Coverage for app/core/security.py — token extraction and JWT verification."""
import pytest
from fastapi import HTTPException

from app.core.security import get_token_from_header, verify_token


# ── get_token_from_header ────────────────────────────────────────────────────

def test_get_token_from_header_valid():
    """Valid Bearer header returns the raw token string."""
    token = get_token_from_header("Bearer eyJhbGciOiJIUzI1NiJ9.test")
    assert token == "eyJhbGciOiJIUzI1NiJ9.test"


def test_get_token_from_header_no_bearer_prefix_raises_401():
    """Header without 'Bearer ' prefix raises 401."""
    with pytest.raises(HTTPException) as exc_info:
        get_token_from_header("Token eyJhbG...")
    assert exc_info.value.status_code == 401


def test_get_token_from_header_empty_string_raises_401():
    """Empty Authorization header raises 401."""
    with pytest.raises(HTTPException) as exc_info:
        get_token_from_header("")
    assert exc_info.value.status_code == 401


def test_get_token_from_header_none_raises_401():
    """None Authorization header raises 401."""
    with pytest.raises(HTTPException) as exc_info:
        get_token_from_header(None)
    assert exc_info.value.status_code == 401


def test_get_token_from_header_bare_bearer_raises_401():
    """'Bearer' with no token raises 401."""
    with pytest.raises(HTTPException) as exc_info:
        get_token_from_header("Bearer")
    assert exc_info.value.status_code == 401


def test_get_token_from_header_strips_only_first_space():
    """Token containing spaces is preserved after the first split."""
    result = get_token_from_header("Bearer abc def")
    assert result == "abc def"


# ── verify_token ─────────────────────────────────────────────────────────────

def test_verify_token_garbage_raises_401():
    """Completely invalid token string raises 401 HTTPException."""
    with pytest.raises(HTTPException) as exc_info:
        verify_token("garbage.token.here")
    assert exc_info.value.status_code == 401


def test_verify_token_empty_string_raises_401():
    """Empty string raises 401 HTTPException."""
    with pytest.raises(HTTPException) as exc_info:
        verify_token("")
    assert exc_info.value.status_code == 401


def test_verify_token_malformed_jwt_raises_401():
    """JWT with wrong number of segments raises 401."""
    with pytest.raises(HTTPException) as exc_info:
        verify_token("onlyone")
    assert exc_info.value.status_code == 401


def test_verify_token_wrong_signature_raises_401():
    """JWT signed with wrong key raises 401."""
    # This is a valid HS256 JWT structure but signed with "wrong-secret"
    bad_token = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        ".eyJzdWIiOiJ1c2VyLTEyMyIsImVtYWlsIjoidGVzdEBhcGV4LmFpIn0"
        ".WRONG_SIGNATURE_PADDING_HERE_X"
    )
    with pytest.raises(HTTPException) as exc_info:
        verify_token(bad_token)
    assert exc_info.value.status_code == 401


def test_verify_token_www_authenticate_header_present():
    """Raised HTTPException includes WWW-Authenticate header."""
    with pytest.raises(HTTPException) as exc_info:
        verify_token("not.a.valid.jwt")
    assert "WWW-Authenticate" in (exc_info.value.headers or {})
