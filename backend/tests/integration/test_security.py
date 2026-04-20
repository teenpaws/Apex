"""
Security tests — SQL injection, XSS, stack trace exposure, CORS.
All tests use USE_MOCK_DATA=true (conftest).
"""

import pytest
import json
from urllib.parse import quote

# SQL injection payloads
SQL_PAYLOADS = [
    "'; DROP TABLE signals; --",
    "' OR '1'='1",
    "1 UNION SELECT * FROM users",
    "' OR 1=1 --",
]

# XSS payloads
XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    '"><svg onload=alert(1)>',
    "<iframe src='javascript:alert(1)'></iframe>",
]


# ─────────────────────────────────────────────────────────────────────────────
# SQL Injection Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", SQL_PAYLOADS)
async def test_sql_injection_in_signal_type(async_client, payload):
    """Verify SQL injection attempts in signal_type filter don't cause 500."""
    r = await async_client.get(f"/api/v1/signals?signal_type={quote(payload)}")
    # Should not crash with 500; may return 200 with empty results, 400 if validation fails
    assert r.status_code != 500, f"SQL injection caused 500: {payload}"
    # Response should be valid JSON, not a traceback
    try:
        data = r.json()
        assert isinstance(data, (dict, list)), "Response must be JSON dict or list"
    except json.JSONDecodeError:
        pytest.fail(f"Response is not valid JSON: {r.text}")


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", SQL_PAYLOADS)
async def test_sql_injection_in_opportunity_status(async_client, payload):
    """Verify SQL injection attempts in status filter don't cause 500."""
    r = await async_client.get(f"/api/v1/opportunities?status={quote(payload)}")
    assert r.status_code != 500, f"SQL injection caused 500: {payload}"
    try:
        data = r.json()
        assert isinstance(data, (dict, list)), "Response must be JSON dict or list"
    except json.JSONDecodeError:
        pytest.fail(f"Response is not valid JSON: {r.text}")


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", SQL_PAYLOADS)
async def test_sql_injection_in_opportunity_confidence(async_client, payload):
    """Verify SQL injection attempts in confidence filter don't cause 500."""
    r = await async_client.get(f"/api/v1/opportunities?confidence={quote(payload)}")
    assert r.status_code != 500, f"SQL injection caused 500: {payload}"
    try:
        data = r.json()
        assert isinstance(data, (dict, list)), "Response must be JSON dict or list"
    except json.JSONDecodeError:
        pytest.fail(f"Response is not valid JSON: {r.text}")


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", SQL_PAYLOADS)
async def test_sql_injection_in_signal_company_id(async_client, payload):
    """Verify SQL injection in company_id filter doesn't cause 500."""
    r = await async_client.get(f"/api/v1/signals?company_id={quote(payload)}")
    assert r.status_code != 500, f"SQL injection caused 500: {payload}"
    try:
        data = r.json()
        assert isinstance(data, (dict, list)), "Response must be JSON dict or list"
    except json.JSONDecodeError:
        pytest.fail(f"Response is not valid JSON: {r.text}")


# ─────────────────────────────────────────────────────────────────────────────
# XSS (Cross-Site Scripting) Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", XSS_PAYLOADS)
async def test_xss_not_reflected_in_signals_response(async_client, payload):
    """Verify XSS payloads are not reflected raw in signal list responses."""
    r = await async_client.get(f"/api/v1/signals?signal_type={quote(payload)}")
    assert r.status_code != 500, f"Payload caused 500: {payload}"
    # Verify dangerous HTML tags are not in the response body
    response_text = r.text.lower()
    assert "<script>" not in response_text, "Response contains unescaped <script> tag"
    assert "onerror=" not in response_text, "Response contains unescaped onerror attribute"
    assert "onload=" not in response_text, "Response contains unescaped onload attribute"


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", XSS_PAYLOADS)
async def test_xss_not_reflected_in_opportunities_response(async_client, payload):
    """Verify XSS payloads are not reflected in opportunity list responses."""
    r = await async_client.get(f"/api/v1/opportunities?status={quote(payload)}")
    assert r.status_code != 500, f"Payload caused 500: {payload}"
    response_text = r.text.lower()
    assert "<script>" not in response_text, "Response contains unescaped <script> tag"
    assert "onerror=" not in response_text, "Response contains unescaped onerror attribute"


# ─────────────────────────────────────────────────────────────────────────────
# Stack Trace Exposure Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_404_no_stack_trace(async_client):
    """Verify 404 responses don't leak stack traces."""
    r = await async_client.get("/api/v1/signals/nonexistent-id-999")
    assert r.status_code == 404
    body = r.json()
    body_str = str(body).lower()
    # Should not contain traceback keywords
    assert "traceback" not in body_str, "404 response contains traceback"
    assert "file " not in body_str or "python" not in body_str, "404 response contains file path"
    # Should have error structure
    assert "error" in body or "detail" in body, "404 response missing error/detail field"


@pytest.mark.asyncio
async def test_invalid_json_no_stack_trace(async_client):
    """Verify malformed JSON doesn't leak stack traces."""
    r = await async_client.post(
        "/api/v1/signals/ingest",
        content="{invalid json",
        headers={"Content-Type": "application/json"},
    )
    # Should return 400 or 422, not 500
    assert r.status_code in (400, 422), f"Expected 400/422, got {r.status_code}"
    # Should not contain Python traceback
    assert "Traceback" not in r.text, "Response contains Traceback keyword"
    assert "File " not in r.text or "line" not in r.text, "Response contains file path info"
    # Should contain error detail
    try:
        body = r.json()
        assert isinstance(body, dict), "Error response should be dict"
    except json.JSONDecodeError:
        pytest.fail(f"Error response is not valid JSON: {r.text}")


@pytest.mark.asyncio
async def test_500_error_no_stack_trace(async_client):
    """Verify 500 errors don't leak stack traces to client."""
    # Send a request with invalid body structure to the ingest endpoint
    r = await async_client.post(
        "/api/v1/signals/ingest",
        json={"invalid_field": "value"},
        headers={"Content-Type": "application/json"},
    )
    # Should be 4xx for bad request or 500 for internal error, but never leak trace
    response_text = r.text
    assert "Traceback" not in response_text, "500 response contains Traceback"
    assert "File " not in response_text or "line" not in response_text, "500 response contains file path"
    # If 500, should have error structure
    if r.status_code >= 500:
        try:
            body = r.json()
            assert "error" in body, "500 response missing error field"
        except json.JSONDecodeError:
            pytest.fail(f"500 response is not valid JSON: {r.text}")


# ─────────────────────────────────────────────────────────────────────────────
# CORS Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cors_headers_present_on_options(async_client):
    """Verify CORS headers are present in OPTIONS response."""
    r = await async_client.options(
        "/api/v1/signals",
        headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Should return 200 for OPTIONS
    assert r.status_code == 200, f"OPTIONS request failed with {r.status_code}"
    # CORS headers should be present (middleware configured with allow_origins=["*"])
    headers = {k.lower(): v for k, v in r.headers.items()}
    assert "access-control-allow-origin" in headers, "Missing Access-Control-Allow-Origin header"
    # With allow_origins=["*"], should echo back the origin or return "*"
    allow_origin = headers.get("access-control-allow-origin", "").lower()
    assert allow_origin in ("*", "https://evil.com"), f"Invalid CORS origin: {allow_origin}"


@pytest.mark.asyncio
async def test_cors_headers_present_on_get(async_client):
    """Verify CORS headers are present in regular GET responses."""
    r = await async_client.get(
        "/api/v1/signals",
        headers={
            "Origin": "https://example.com",
        },
    )
    # Should be successful
    assert r.status_code == 200, f"GET request failed with {r.status_code}"
    headers = {k.lower(): v for k, v in r.headers.items()}
    # CORS headers should be present
    assert "access-control-allow-origin" in headers, "Missing Access-Control-Allow-Origin header"


@pytest.mark.asyncio
async def test_cors_allow_credentials_set(async_client):
    """Verify CORS credentials flag is set appropriately."""
    r = await async_client.options(
        "/api/v1/opportunities",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    # Check for credentials header (may be true or false, but should be present)
    headers = {k.lower(): v for k, v in r.headers.items()}
    # If credentials allowed, this header may be present
    if "access-control-allow-credentials" in headers:
        value = headers["access-control-allow-credentials"].lower()
        assert value in ("true", "false"), f"Invalid credentials value: {value}"


# ─────────────────────────────────────────────────────────────────────────────
# Error Response Format Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_error_response_format(async_client):
    """Verify error responses follow the ErrorDetail schema."""
    r = await async_client.get("/api/v1/signals/nonexistent-id")
    assert r.status_code == 404
    body = r.json()
    # Should have error field (based on ErrorDetail schema)
    assert "error" in body, "Error response missing 'error' field"
    assert isinstance(body["error"], str), "'error' field should be string"
    # May have detail and code fields
    if "detail" in body:
        assert isinstance(body.get("detail"), (str, type(None))), "'detail' field should be string or null"
    if "code" in body:
        assert isinstance(body.get("code"), (str, type(None))), "'code' field should be string or null"


@pytest.mark.asyncio
async def test_validation_error_response_format(async_client):
    """Verify validation errors follow a consistent schema."""
    r = await async_client.get("/api/v1/signals?page=-1")  # Invalid: page must be >= 1
    # Should be 422 (validation error) or 400 (bad request)
    assert r.status_code in (400, 422), f"Expected 400/422, got {r.status_code}"
    body = r.json()
    # FastAPI validation errors have detail field
    assert isinstance(body, dict), "Validation error response should be dict"
