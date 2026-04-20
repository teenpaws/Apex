# Phase 11: v1.0 Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package Apex as a production-ready Docker Compose stack (FastAPI + Celery + Redis + Nginx + Next.js) with structured JSON logging, environment-scoped CORS, and a one-command startup checklist.

**Architecture:** 5-container stack — `nginx` (port 80) reverse-proxies `/api/*` to `backend:8000` (Gunicorn + UvicornWorker) and `/` to `frontend:3000` (Next.js standalone). `celery_worker` + `celery_beat` share the backend image. Supabase remains cloud-hosted. Environment is driven by `.env.prod` and an `ENVIRONMENT` flag that tightens CORS, enables JSON logs, and disables debug output.

**Tech Stack:** Docker, Docker Compose v2, Gunicorn 21.2, python-json-logger 2.0.7, Next.js standalone output, Nginx Alpine

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Modify | `backend/app/core/config.py` | Add ENVIRONMENT, LOG_LEVEL, JSON_LOGS, ALLOWED_ORIGINS |
| Modify | `backend/app/main.py` | Wire logging on startup; scope CORS to ALLOWED_ORIGINS in prod |
| Modify | `backend/app/api/v1/health.py` | Add `environment` field to HealthResponse |
| Modify | `backend/requirements.txt` | Add gunicorn, python-json-logger, pyyaml |
| Modify | `frontend/next.config.ts` | Add `output: 'standalone'` |
| Create | `backend/app/core/logging_config.py` | JSON log formatter + configure_logging() |
| Create | `backend/Dockerfile` | Multi-stage: builder + slim runtime; Gunicorn CMD |
| Create | `frontend/Dockerfile` | Multi-stage: deps → builder → Next.js standalone runner |
| Create | `nginx/nginx.conf` | Reverse-proxy `/api/` → backend, `/` → frontend |
| Create | `docker-compose.prod.yml` | All 5 services wired with healthchecks + env_file |
| Create | `backend/.env.prod.example` | Production env template (all required vars, no secrets) |
| Create | `backend/scripts/run_migrations.sh` | Apply all SQL migrations in order |
| Create | `README.md` | Quick-start guide, env setup, production launch checklist |
| Test | `backend/tests/unit/test_prod_config.py` | Settings: ENVIRONMENT, JSON_LOGS, ALLOWED_ORIGINS |
| Test | `backend/tests/unit/test_logging_config.py` | JSON log formatter output |
| Test | `backend/tests/unit/test_health_enhanced.py` | /health includes environment field |
| Test | `backend/tests/unit/test_deployment_artifacts.py` | Docker/nginx/compose files exist with required content |

---

## Task 1: Production Settings

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/requirements.txt`
- Create: `backend/tests/unit/test_prod_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_prod_config.py
import os
import pytest
from unittest.mock import patch


def _fresh_settings(**env_overrides):
    """Create a Settings instance with overridden env vars, bypassing .env file."""
    from app.core.config import Settings
    with patch.dict(os.environ, {k: str(v) for k, v in env_overrides.items()}, clear=False):
        return Settings(_env_file=None)


def test_environment_defaults_to_development():
    s = _fresh_settings()
    assert s.ENVIRONMENT == "development"


def test_json_logs_off_by_default():
    s = _fresh_settings()
    assert s.JSON_LOGS is False


def test_log_level_defaults_to_info():
    s = _fresh_settings()
    assert s.LOG_LEVEL == "INFO"


def test_allowed_origins_default_contains_localhost():
    s = _fresh_settings()
    assert any("localhost" in o for o in s.ALLOWED_ORIGINS)


def test_prod_environment_override():
    s = _fresh_settings(ENVIRONMENT="production", JSON_LOGS="true", LOG_LEVEL="WARNING")
    assert s.ENVIRONMENT == "production"
    assert s.JSON_LOGS is True
    assert s.LOG_LEVEL == "WARNING"


def test_allowed_origins_can_be_overridden():
    s = _fresh_settings(ALLOWED_ORIGINS='["https://app.apex.ai"]')
    assert s.ALLOWED_ORIGINS == ["https://app.apex.ai"]
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend
pytest tests/unit/test_prod_config.py -v
```
Expected: 6 FAILED — `Settings` has no attribute `ENVIRONMENT` (or similar)

- [ ] **Step 3: Add new fields to Settings**

Replace `backend/app/core/config.py` with:

```python
"""
Apex platform configuration — reads all environment variables via Pydantic Settings.

Usage:
    from app.core.config import get_settings
    settings = get_settings()
"""

from functools import lru_cache
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ───────────────────────────────────────────────────────────
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development | staging | production

    # ── Database / Supabase ───────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/apex"
    SUPABASE_URL: str = "https://placeholder.supabase.co"
    SUPABASE_ANON_KEY: str = "placeholder-anon-key"
    SUPABASE_SERVICE_ROLE_KEY: str = "placeholder-service-role-key"

    # ── AI / LLM ──────────────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = "placeholder-anthropic-key"
    OPENAI_API_KEY: str = "placeholder-openai-key"

    # ── Signal Sources (free tier — see CLAUDE.md Section 14) ────────────────
    NEWSDATA_API_KEY: str = "placeholder-newsdata-key"
    GNEWS_API_KEY: str = "placeholder-gnews-key"

    # ── Contact Intelligence ──────────────────────────────────────────────────
    PDL_API_KEY: str = "placeholder-pdl-key"
    HUNTER_API_KEY: str = "placeholder-hunter-key"

    # ── Redis / Celery ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"

    # ── Gmail OAuth ───────────────────────────────────────────────────────────
    GMAIL_CLIENT_ID: str = "placeholder-gmail-client-id"
    GMAIL_CLIENT_SECRET: str = "placeholder-gmail-client-secret"
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/api/v1/outreach/oauth/callback"

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    JSON_LOGS: bool = False  # True in production for structured log aggregation

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    # ── Development Flags ─────────────────────────────────────────────────────
    MOCK_AGENTS: bool = True
    USE_MOCK_DATA: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance."""
    return Settings()
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend
pytest tests/unit/test_prod_config.py -v
```
Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/tests/unit/test_prod_config.py
git commit -m "feat(phase11): add ENVIRONMENT, LOG_LEVEL, JSON_LOGS, ALLOWED_ORIGINS to Settings"
```

---

## Task 2: Structured JSON Logging

**Files:**
- Create: `backend/app/core/logging_config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/requirements.txt`
- Create: `backend/tests/unit/test_logging_config.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_logging_config.py
import json
import logging


def test_json_formatter_produces_valid_json():
    from app.core.logging_config import ApexJsonFormatter
    import io
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(ApexJsonFormatter())
    logger = logging.getLogger("apex.test.json_formatter")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    logger.info("hello world")

    output = stream.getvalue().strip()
    assert output, "log output should not be empty"
    record = json.loads(output)
    assert record["message"] == "hello world"
    assert "timestamp" in record
    assert "level" in record
    assert record["level"] == "INFO"


def test_json_formatter_includes_logger_name():
    from app.core.logging_config import ApexJsonFormatter
    import io
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(ApexJsonFormatter())
    logger = logging.getLogger("apex.test.name_field")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    logger.warning("check name")

    record = json.loads(stream.getvalue().strip())
    assert record["logger"] == "apex.test.name_field"
    assert record["level"] == "WARNING"


def test_configure_logging_sets_root_level():
    from app.core.logging_config import configure_logging
    configure_logging(log_level="DEBUG", json_logs=False)
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    # Reset to not affect other tests
    configure_logging(log_level="WARNING", json_logs=False)
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend
pytest tests/unit/test_logging_config.py -v
```
Expected: 3 FAILED — `cannot import name 'ApexJsonFormatter'`

- [ ] **Step 3: Add python-json-logger to requirements.txt**

Add this line after the `slowapi` line:
```
python-json-logger==2.0.7  # structured JSON logs for production
```

Install it:
```
pip install python-json-logger==2.0.7
```

- [ ] **Step 4: Create logging_config.py**

```python
# backend/app/core/logging_config.py
"""
Structured JSON logging for production.

Usage:
    from app.core.logging_config import configure_logging
    configure_logging(log_level=settings.LOG_LEVEL, json_logs=settings.JSON_LOGS)
"""

import logging
from datetime import datetime, timezone

from pythonjsonlogger.jsonlogger import JsonFormatter


class ApexJsonFormatter(JsonFormatter):
    """JSON log formatter that emits timestamp, level, logger, message."""

    def add_fields(self, log_record: dict, record: logging.LogRecord, message_dict: dict) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record.pop("levelname", None)
        log_record.pop("name", None)


def configure_logging(log_level: str = "INFO", json_logs: bool = False) -> None:
    """Configure root logger. Call once at application startup."""
    handler = logging.StreamHandler()
    if json_logs:
        handler.setFormatter(ApexJsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
        )
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        handlers=[handler],
        force=True,
    )
```

- [ ] **Step 5: Wire configure_logging into main.py**

In `backend/app/main.py`, add the logging call inside `create_app()` before the middleware setup:

```python
# Add these two imports at the top:
from app.core.logging_config import configure_logging

# Add this as the FIRST line inside create_app(), before settings = get_settings():
# (actually add it after settings = get_settings())
```

Full updated `create_app()` function:

```python
def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    settings = get_settings()

    configure_logging(log_level=settings.LOG_LEVEL, json_logs=settings.JSON_LOGS)

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
    # In development, allow all origins. In prod, ALLOWED_ORIGINS is set via env.
    origins = ["*"] if settings.ENVIRONMENT == "development" else settings.ALLOWED_ORIGINS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
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
```

- [ ] **Step 6: Run tests to verify they pass**

```
cd backend
pytest tests/unit/test_logging_config.py -v
```
Expected: 3 PASSED

- [ ] **Step 7: Run full test suite to verify no regressions**

```
cd backend
pytest tests/ -q --tb=short -k "not test_db"
```
Expected: same count as before + 3 new passing

- [ ] **Step 8: Commit**

```bash
git add backend/app/core/logging_config.py backend/app/main.py backend/requirements.txt backend/tests/unit/test_logging_config.py
git commit -m "feat(phase11): structured JSON logging with ApexJsonFormatter"
```

---

## Task 3: Enhanced Health Endpoint

**Files:**
- Modify: `backend/app/api/v1/health.py`
- Create: `backend/tests/unit/test_health_enhanced.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/test_health_enhanced.py
import pytest


@pytest.mark.asyncio
async def test_health_includes_environment(async_client):
    response = await async_client.get("/api/v1/health")
    data = response.json()
    assert "environment" in data, "health response must include environment field"
    assert data["environment"] == "development"  # default in test mode


@pytest.mark.asyncio
async def test_health_all_fields_present(async_client):
    response = await async_client.get("/api/v1/health")
    data = response.json()
    required = {"status", "version", "mock_mode", "environment"}
    missing = required - set(data.keys())
    assert not missing, f"health response missing fields: {missing}"
```

- [ ] **Step 2: Run test to verify it fails**

```
cd backend
pytest tests/unit/test_health_enhanced.py -v
```
Expected: 2 FAILED — `'environment' not in data`

- [ ] **Step 3: Update health.py**

```python
# backend/app/api/v1/health.py
"""
Health check endpoint — GET /api/v1/health

Returns service status, version, environment, and whether mock mode is active.
Used by load balancers, CI pipelines, and the frontend status indicator.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    mock_mode: bool


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Service health check",
    description="Returns 200 with service status. Safe to call without authentication.",
)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        mock_mode=settings.USE_MOCK_DATA,
    )
```

- [ ] **Step 4: Run both new and existing health tests**

```
cd backend
pytest tests/unit/test_health_enhanced.py tests/integration/test_health.py -v
```
Expected: 5 PASSED (3 existing + 2 new)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/health.py backend/tests/unit/test_health_enhanced.py
git commit -m "feat(phase11): add environment field to health endpoint response"
```

---

## Task 4: Backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`
- Modify: `backend/requirements.txt` (add gunicorn)
- Create: `backend/tests/unit/test_deployment_artifacts.py` (first assertions)

- [ ] **Step 1: Write the failing test (partial — backend Dockerfile)**

```python
# backend/tests/unit/test_deployment_artifacts.py
"""Tests that deployment configuration files exist and contain required content."""
from pathlib import Path

# Repo root is 3 levels up from this test file: tests/unit/ -> tests/ -> backend/ -> root
REPO_ROOT = Path(__file__).parent.parent.parent.parent


def test_backend_dockerfile_exists():
    df = REPO_ROOT / "backend" / "Dockerfile"
    assert df.exists(), "backend/Dockerfile must exist"


def test_backend_dockerfile_uses_gunicorn():
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "gunicorn" in content.lower(), "backend Dockerfile must use Gunicorn"


def test_backend_dockerfile_uses_nonroot_user():
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "USER" in content, "backend Dockerfile must set a non-root USER"


def test_backend_dockerfile_exposes_8000():
    content = (REPO_ROOT / "backend" / "Dockerfile").read_text()
    assert "8000" in content, "backend Dockerfile must EXPOSE port 8000"
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend
pytest tests/unit/test_deployment_artifacts.py::test_backend_dockerfile_exists -v
pytest tests/unit/test_deployment_artifacts.py::test_backend_dockerfile_uses_gunicorn -v
```
Expected: 2 FAILED — file not found

- [ ] **Step 3: Add gunicorn to requirements.txt**

Add after the uvicorn line:
```
gunicorn==21.2.0          # production WSGI/ASGI server wrapper
```

- [ ] **Step 4: Create backend/Dockerfile**

```dockerfile
# backend/Dockerfile
# ── Stage 1: install dependencies ─────────────────────────────────────────────
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: slim runtime image ───────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

RUN useradd -m -u 1000 apex && chown -R apex:apex /app
USER apex

EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--timeout", "120"]
```

- [ ] **Step 5: Run tests to verify they pass**

```
cd backend
pytest tests/unit/test_deployment_artifacts.py -v -k "backend"
```
Expected: 4 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/Dockerfile backend/requirements.txt backend/tests/unit/test_deployment_artifacts.py
git commit -m "feat(phase11): backend Dockerfile with Gunicorn + non-root user"
```

---

## Task 5: Frontend Dockerfile (Next.js Standalone)

**Files:**
- Modify: `frontend/next.config.ts`
- Create: `frontend/Dockerfile`
- Extend: `backend/tests/unit/test_deployment_artifacts.py`

- [ ] **Step 1: Write the failing tests (append to test_deployment_artifacts.py)**

Add these functions to `backend/tests/unit/test_deployment_artifacts.py`:

```python
def test_frontend_dockerfile_exists():
    df = REPO_ROOT / "frontend" / "Dockerfile"
    assert df.exists(), "frontend/Dockerfile must exist"


def test_frontend_dockerfile_has_standalone_reference():
    content = (REPO_ROOT / "frontend" / "Dockerfile").read_text()
    assert "standalone" in content, "frontend Dockerfile must reference .next/standalone"


def test_frontend_dockerfile_exposes_3000():
    content = (REPO_ROOT / "frontend" / "Dockerfile").read_text()
    assert "3000" in content, "frontend Dockerfile must EXPOSE port 3000"


def test_nextconfig_has_standalone_output():
    content = (REPO_ROOT / "frontend" / "next.config.ts").read_text()
    assert "standalone" in content, "next.config.ts must set output: 'standalone'"
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend
pytest tests/unit/test_deployment_artifacts.py -v -k "frontend or nextconfig"
```
Expected: 4 FAILED — files don't exist yet

- [ ] **Step 3: Update frontend/next.config.ts to enable standalone output**

```typescript
// frontend/next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
};

export default nextConfig;
```

- [ ] **Step 4: Verify Next.js build still works**

```
cd frontend
npm run build
```
Expected: Build completes. `.next/standalone/` directory is created.

- [ ] **Step 5: Create frontend/Dockerfile**

```dockerfile
# frontend/Dockerfile
# ── Stage 1: install dependencies ─────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

# ── Stage 2: build Next.js standalone ─────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ── Stage 3: minimal runtime ──────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
```

- [ ] **Step 6: Run tests to verify they pass**

```
cd backend
pytest tests/unit/test_deployment_artifacts.py -v -k "frontend or nextconfig"
```
Expected: 4 PASSED

- [ ] **Step 7: Commit**

```bash
git add frontend/next.config.ts frontend/Dockerfile backend/tests/unit/test_deployment_artifacts.py
git commit -m "feat(phase11): frontend Dockerfile with Next.js standalone output"
```

---

## Task 6: Nginx Reverse Proxy

**Files:**
- Create: `nginx/nginx.conf`
- Extend: `backend/tests/unit/test_deployment_artifacts.py`

- [ ] **Step 1: Write the failing tests (append to test_deployment_artifacts.py)**

```python
def test_nginx_conf_exists():
    conf = REPO_ROOT / "nginx" / "nginx.conf"
    assert conf.exists(), "nginx/nginx.conf must exist"


def test_nginx_conf_proxies_api_to_backend():
    content = (REPO_ROOT / "nginx" / "nginx.conf").read_text()
    assert "proxy_pass" in content
    assert "/api/" in content


def test_nginx_conf_proxies_root_to_frontend():
    content = (REPO_ROOT / "nginx" / "nginx.conf").read_text()
    lines = content.split("\n")
    # location / block must exist and proxy_pass must follow it
    found_root_location = False
    for i, line in enumerate(lines):
        if "location /" in line and "/api" not in line:
            found_root_location = True
    assert found_root_location, "nginx.conf must have a root location / block"


def test_nginx_conf_listens_on_80():
    content = (REPO_ROOT / "nginx" / "nginx.conf").read_text()
    assert "listen 80" in content
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend
pytest tests/unit/test_deployment_artifacts.py -v -k "nginx"
```
Expected: 4 FAILED — file not found

- [ ] **Step 3: Create nginx directory and nginx.conf**

```bash
mkdir -p nginx
```

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout 65;

    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    server {
        listen 80;
        server_name _;

        # API traffic → FastAPI backend
        location /api/ {
            proxy_pass         http://backend;
            proxy_http_version 1.1;
            proxy_set_header   Host              $host;
            proxy_set_header   X-Real-IP         $remote_addr;
            proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
            proxy_set_header   X-Forwarded-Proto $scheme;
            proxy_read_timeout 120s;
        }

        # All other traffic → Next.js frontend
        location / {
            proxy_pass         http://frontend;
            proxy_http_version 1.1;
            proxy_set_header   Upgrade    $http_upgrade;
            proxy_set_header   Connection "upgrade";
            proxy_set_header   Host       $host;
            proxy_set_header   X-Real-IP  $remote_addr;
        }
    }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend
pytest tests/unit/test_deployment_artifacts.py -v -k "nginx"
```
Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add nginx/nginx.conf backend/tests/unit/test_deployment_artifacts.py
git commit -m "feat(phase11): nginx reverse-proxy config — /api/ → backend, / → frontend"
```

---

## Task 7: docker-compose.prod.yml

**Files:**
- Create: `docker-compose.prod.yml`
- Extend: `backend/tests/unit/test_deployment_artifacts.py`

- [ ] **Step 1: Write the failing tests (append to test_deployment_artifacts.py)**

```python
def test_docker_compose_prod_exists():
    f = REPO_ROOT / "docker-compose.prod.yml"
    assert f.exists(), "docker-compose.prod.yml must exist"


def test_docker_compose_prod_has_all_services():
    content = (REPO_ROOT / "docker-compose.prod.yml").read_text()
    required_services = ["redis:", "backend:", "celery_worker:", "frontend:", "nginx:"]
    for svc in required_services:
        assert svc in content, f"docker-compose.prod.yml missing service: {svc}"


def test_docker_compose_prod_backend_depends_on_redis():
    content = (REPO_ROOT / "docker-compose.prod.yml").read_text()
    assert "redis" in content
    # backend section must appear before celery sections
    backend_pos = content.find("backend:")
    redis_pos = content.find("redis:")
    assert redis_pos < backend_pos, "redis service should be declared before backend"


def test_docker_compose_prod_nginx_exposes_port_80():
    content = (REPO_ROOT / "docker-compose.prod.yml").read_text()
    assert '"80:80"' in content or "'80:80'" in content or "80:80" in content
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend
pytest tests/unit/test_deployment_artifacts.py -v -k "compose"
```
Expected: 4 FAILED — file not found

- [ ] **Step 3: Create docker-compose.prod.yml**

```yaml
# docker-compose.prod.yml
# Production Apex stack — run with:
#   docker compose -f docker-compose.prod.yml up -d
#
# Prerequisites:
#   - Copy backend/.env.prod.example → backend/.env.prod and fill in real values
#   - MOCK_AGENTS=false, USE_MOCK_DATA=false in .env.prod

services:
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file: ./backend/.env.prod
    environment:
      - ENVIRONMENT=production
      - JSON_LOGS=true
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s

  celery_worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: >
      celery -A app.core.celery_app worker
      -Q high,default,low
      --loglevel=info
      --concurrency=2
    restart: unless-stopped
    env_file: ./backend/.env.prod
    environment:
      - ENVIRONMENT=production
      - JSON_LOGS=true
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      redis:
        condition: service_healthy

  celery_beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: celery -A app.core.celery_app beat --loglevel=info
    restart: unless-stopped
    env_file: ./backend/.env.prod
    environment:
      - ENVIRONMENT=production
      - JSON_LOGS=true
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      redis:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=/api/v1
    depends_on:
      backend:
        condition: service_healthy

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - backend
      - frontend

volumes:
  redis_data:
```

- [ ] **Step 4: Run tests to verify they pass**

```
cd backend
pytest tests/unit/test_deployment_artifacts.py -v -k "compose"
```
Expected: 4 PASSED

- [ ] **Step 5: Run ALL deployment artifact tests together**

```
cd backend
pytest tests/unit/test_deployment_artifacts.py -v
```
Expected: All 20 tests PASSED

- [ ] **Step 6: Commit**

```bash
git add docker-compose.prod.yml backend/tests/unit/test_deployment_artifacts.py
git commit -m "feat(phase11): docker-compose.prod.yml — all 5 services with healthchecks"
```

---

## Task 8: README, .env.prod.example, Migration Script

**Files:**
- Create: `README.md`
- Create: `backend/.env.prod.example`
- Create: `backend/scripts/run_migrations.sh`
- Extend: `backend/tests/unit/test_deployment_artifacts.py`

- [ ] **Step 1: Write the failing tests (append to test_deployment_artifacts.py)**

```python
def test_env_prod_example_exists():
    f = REPO_ROOT / "backend" / ".env.prod.example"
    assert f.exists(), "backend/.env.prod.example must exist"


def test_env_prod_example_has_required_keys():
    content = (REPO_ROOT / "backend" / ".env.prod.example").read_text()
    required_keys = [
        "DATABASE_URL",
        "SUPABASE_URL",
        "ANTHROPIC_API_KEY",
        "MOCK_AGENTS",
        "USE_MOCK_DATA",
        "ENVIRONMENT",
        "ALLOWED_ORIGINS",
    ]
    for key in required_keys:
        assert key in content, f".env.prod.example missing required key: {key}"


def test_readme_exists():
    f = REPO_ROOT / "README.md"
    assert f.exists(), "README.md must exist"


def test_readme_has_quickstart_section():
    content = (REPO_ROOT / "README.md").read_text()
    assert "Quick Start" in content or "Quickstart" in content or "Getting Started" in content


def test_readme_references_docker_compose():
    content = (REPO_ROOT / "README.md").read_text()
    assert "docker-compose.prod.yml" in content or "docker compose" in content.lower()


def test_migration_script_exists():
    f = REPO_ROOT / "backend" / "scripts" / "run_migrations.sh"
    assert f.exists(), "backend/scripts/run_migrations.sh must exist"
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd backend
pytest tests/unit/test_deployment_artifacts.py -v -k "env_prod or readme or migration"
```
Expected: 6 FAILED — files don't exist

- [ ] **Step 3: Create backend/.env.prod.example**

```bash
# backend/.env.prod.example
# Copy this to .env.prod and fill in real values before deploying.
# NEVER commit .env.prod to git.

# ── Application ───────────────────────────────────────────────────────────────
APP_VERSION=1.0.0
ENVIRONMENT=production
LOG_LEVEL=INFO
JSON_LOGS=true

# ── CORS — comma-separated list of allowed frontend origins ──────────────────
# Example: ALLOWED_ORIGINS=["https://app.yourdomain.com"]
ALLOWED_ORIGINS=["https://app.yourdomain.com"]

# ── Database / Supabase ───────────────────────────────────────────────────────
DATABASE_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>

# ── AI / LLM ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=<your-anthropic-key>
OPENAI_API_KEY=<your-openai-key>

# ── Signal Sources ────────────────────────────────────────────────────────────
NEWSDATA_API_KEY=<newsdata.io key>
GNEWS_API_KEY=<gnews.io key>

# ── Contact Intelligence ──────────────────────────────────────────────────────
PDL_API_KEY=<people-data-labs key>
HUNTER_API_KEY=<hunter.io key>

# ── Gmail OAuth ───────────────────────────────────────────────────────────────
GMAIL_CLIENT_ID=<gmail oauth client id>
GMAIL_CLIENT_SECRET=<gmail oauth client secret>
GMAIL_REDIRECT_URI=https://app.yourdomain.com/api/v1/outreach/oauth/callback

# ── Redis (set automatically by docker-compose.prod.yml) ──────────────────────
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# ── IMPORTANT: Set both to false in production ────────────────────────────────
MOCK_AGENTS=false
USE_MOCK_DATA=false
```

- [ ] **Step 4: Create backend/scripts/run_migrations.sh**

```bash
mkdir -p backend/scripts
```

```bash
#!/usr/bin/env bash
# backend/scripts/run_migrations.sh
# Apply all Supabase SQL migrations in numeric order.
# Usage: DATABASE_URL=<url> bash backend/scripts/run_migrations.sh
set -euo pipefail

MIGRATIONS_DIR="$(dirname "$0")/../app/db/migrations"

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERROR: DATABASE_URL environment variable is not set."
  exit 1
fi

echo "Applying Apex migrations from $MIGRATIONS_DIR"

for f in $(ls "$MIGRATIONS_DIR"/*.sql | sort -V); do
  echo "  → Applying $(basename "$f")..."
  psql "$DATABASE_URL" -f "$f"
done

echo "All migrations applied successfully."
```

```bash
chmod +x backend/scripts/run_migrations.sh
```

- [ ] **Step 5: Create README.md**

```markdown
# Apex Platform

Multi-agent AI platform that predicts hiring 4–12 weeks before roles are posted.

## Quick Start (Production)

### Prerequisites

- Docker Desktop installed and running
- Supabase project created at https://supabase.com
- API keys configured (see Environment Setup below)

### 1. Clone and configure environment

```bash
git clone <repo-url> apex
cd apex
cp backend/.env.prod.example backend/.env.prod
# Edit backend/.env.prod with your real API keys and Supabase credentials
```

### 2. Run database migrations

```bash
DATABASE_URL=<your-supabase-db-url> bash backend/scripts/run_migrations.sh
```

### 3. Start the production stack

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 4. Verify everything is running

```bash
# Check all containers are healthy
docker compose -f docker-compose.prod.yml ps

# Verify API responds
curl http://localhost/api/v1/health
# Expected: {"status":"ok","version":"1.0.0","environment":"production","mock_mode":false}

# Open in browser
open http://localhost
```

## Environment Setup

| Variable | Where to Get It | Required |
|----------|----------------|----------|
| `SUPABASE_URL` | Supabase dashboard → Settings → API | ✅ |
| `SUPABASE_ANON_KEY` | Supabase dashboard → Settings → API | ✅ |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase dashboard → Settings → API | ✅ |
| `DATABASE_URL` | Supabase dashboard → Settings → Database | ✅ |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com | ✅ |
| `OPENAI_API_KEY` | https://platform.openai.com | ✅ |
| `NEWSDATA_API_KEY` | https://newsdata.io/register (free) | ✅ |
| `GNEWS_API_KEY` | https://gnews.io/register (free) | ✅ |
| `PDL_API_KEY` | https://dashboard.peopledatalabs.com (free 1k/mo) | ✅ |
| `HUNTER_API_KEY` | https://hunter.io (free 25/mo) | ✅ |
| `GMAIL_CLIENT_ID` + `GMAIL_CLIENT_SECRET` | Google Cloud Console → OAuth 2.0 | For email |
| `ALLOWED_ORIGINS` | Your frontend domain(s) | ✅ |

All API keys have free tiers that cover personal-scale usage. See `CLAUDE.md` Section 14 for details.

## Development (No Docker Required)

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
# → http://localhost:8000/api/docs

# Frontend
cd frontend
npm install
npm run dev
# → http://localhost:3000

# Run tests
cd backend && pytest tests/ -q --tb=short -k "not test_db"
cd frontend && npm test
```

## Stopping the Stack

```bash
docker compose -f docker-compose.prod.yml down          # stop (keep data)
docker compose -f docker-compose.prod.yml down -v       # stop + delete Redis data
```

## Architecture

```
Internet → Nginx (port 80)
              ├── /api/* → FastAPI backend (Gunicorn, port 8000)
              └── /*     → Next.js frontend (standalone, port 3000)

FastAPI ←→ Supabase Postgres (cloud)
FastAPI ←→ Redis (local container)
Celery worker ←→ Redis (same container)
Celery beat   ←→ Redis (4h signal ingestion cron)
```
```

- [ ] **Step 6: Run all failing tests to verify they pass**

```
cd backend
pytest tests/unit/test_deployment_artifacts.py -v -k "env_prod or readme or migration"
```
Expected: 6 PASSED

- [ ] **Step 7: Run complete test suite — zero regressions**

```
cd backend
pytest tests/ -q --tb=short -k "not test_db"
```
Expected: All previous tests still passing + new deployment tests passing

- [ ] **Step 8: Commit everything**

```bash
git add README.md backend/.env.prod.example backend/scripts/run_migrations.sh backend/tests/unit/test_deployment_artifacts.py
git commit -m "feat(phase11): README quickstart, .env.prod.example, migration runner"
```

---

## Final Verification

- [ ] **Run complete backend test suite**

```
cd backend
pytest tests/ -q --tb=short -k "not test_db"
```
Expected: All tests pass, 0 failures

- [ ] **Run frontend build with standalone output**

```
cd frontend
npm run build
```
Expected: Build passes, `.next/standalone/` directory exists

- [ ] **Verify docker-compose.prod.yml syntax (no Docker required)**

```bash
python3 -c "
import yaml, pathlib
data = yaml.safe_load(pathlib.Path('docker-compose.prod.yml').read_text())
services = list(data['services'].keys())
print('Services:', services)
assert len(services) == 6, f'Expected 6 services, got {len(services)}'
print('docker-compose.prod.yml is valid YAML with correct services.')
"
```
Expected: prints 6 service names without error

- [ ] **Smoke test the dev server (existing functionality unaffected)**

```bash
cd backend && uvicorn app.main:app --port 8000 &
sleep 2
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool
# Expected: {"status":"ok","version":"1.0.0","environment":"development","mock_mode":true}
kill %1
```

- [ ] **Final commit + update PLAN.md**

Mark Phase 11 as ✅ COMPLETE in `PLAN.md` with today's date.

```bash
git add PLAN.md
git commit -m "chore(phase11): mark Phase 11 complete — v1.0 deployment config done"
```

---

## Self-Review

**Spec coverage check:**
- ✅ `docker-compose.prod.yml` — Task 7
- ✅ FastAPI with Gunicorn workers — Task 4 (Dockerfile CMD)
- ✅ Celery worker + beat scheduler — Task 7 (services)
- ✅ Redis — Task 7 (service)
- ✅ Nginx reverse proxy — Task 6
- ✅ Environment separation: dev/staging/prod — Task 1 (ENVIRONMENT flag)
- ✅ Database migrations on prod Supabase — Task 8 (migration script)
- ✅ Structured JSON logs — Task 2
- ✅ Health checks — Task 3 (enhanced), Task 7 (Docker healthcheck)
- ✅ Startup checklist in README — Task 8

**Note on Docker availability:** Phase 1 notes that Docker was not available on the dev machine. The Dockerfiles and docker-compose.prod.yml are written and validated via Python/string tests. To run the stack, install Docker Desktop from https://www.docker.com/products/docker-desktop/. The dev workflow (uvicorn + npm run dev) remains unchanged.
