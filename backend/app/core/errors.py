"""
Structured error handling for the Apex API.

All API errors use the ErrorDetail shape so clients can reliably parse errors:
    {"error": "Human-readable message", "detail": "Optional context", "code": "MACHINE_CODE"}

Usage:
    raise ApexHTTPException(status_code=401, error="Invalid credentials", code="AUTH_INVALID_CREDENTIALS")
"""

import logging
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class ErrorDetail(BaseModel):
    """Canonical error response shape for all Apex API errors."""

    model_config = ConfigDict(extra="forbid")

    error: str
    detail: str | None = None
    code: str | None = None


class ApexHTTPException(HTTPException):
    """
    Apex-specific HTTP exception that carries structured error metadata.

    Attributes:
        status_code: HTTP status code (e.g. 401, 404).
        error:       Short human-readable message.
        detail:      Optional longer explanation (default None).
        code:        Machine-readable error code string (e.g. "AUTH_INVALID_CREDENTIALS").
    """

    def __init__(
        self,
        status_code: int,
        error: str,
        detail: str | None = None,
        code: str | None = None,
    ) -> None:
        # Pass error as HTTPException detail so Starlette internals work correctly.
        super().__init__(status_code=status_code, detail=error)
        self.error = error
        self.error_detail = detail
        self.code = code


async def apex_exception_handler(request: Request, exc: ApexHTTPException) -> JSONResponse:
    """
    Exception handler for ApexHTTPException.

    Returns a JSONResponse with ErrorDetail shape and the exception's status code.
    Register in create_app():
        app.add_exception_handler(ApexHTTPException, apex_exception_handler)
    """
    body = ErrorDetail(
        error=exc.error,
        detail=exc.error_detail,
        code=exc.code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions (500 Internal Server Error).

    Logs the full traceback at ERROR level so it's visible in structured logs,
    but never leaks internal details to the client.

    Register in create_app():
        app.add_exception_handler(Exception, unhandled_exception_handler)
    """
    logger.error(
        "Unhandled exception on %s %s\n%s",
        request.method,
        request.url.path,
        traceback.format_exc(),
    )
    body = ErrorDetail(
        error="Internal server error",
        detail=None,
        code="INTERNAL_ERROR",
    )
    return JSONResponse(
        status_code=500,
        content=body.model_dump(),
    )
