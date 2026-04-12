"""
Apex API — FastAPI application factory.

Entry point:
    uvicorn app.main:app --reload
or:
    python -m app.main
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.errors import (
    ApexHTTPException,
    apex_exception_handler,
    unhandled_exception_handler,
)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title="Apex API",
        description=(
            "Multi-agent AI platform giving job seekers an unfair advantage. "
            "Predicts hiring 4–12 weeks before roles are posted."
        ),
        version=settings.APP_VERSION,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    # ── Middleware ─────────────────────────────────────────────────────────────
    # In development, allow all origins. Tighten this before production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Exception Handlers ─────────────────────────────────────────────────────
    app.add_exception_handler(ApexHTTPException, apex_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(v1_router, prefix="/api/v1")

    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
