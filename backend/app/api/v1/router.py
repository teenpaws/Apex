"""
API v1 aggregate router.

All sub-routers for v1 are registered here. Phase 1 includes only the
health router. Remaining routers are added in subsequent phases.
"""

from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.signals import router as signals_router
from app.api.v1.companies import router as companies_router
from app.api.v1.opportunities import router as opportunities_router
from app.api.v1.actions import router as actions_router
from app.api.v1.profile import router as profile_router
from app.api.v1.contacts import router as contacts_router
from app.api.v1.outreach import router as outreach_router

router = APIRouter()

# ── Phase 1: Infrastructure ────────────────────────────────────────────────────
router.include_router(health_router)

# ── Phase 2: Auth + Core APIs ──────────────────────────────────────────────────
router.include_router(auth_router)
router.include_router(signals_router)
router.include_router(companies_router)
router.include_router(opportunities_router)
router.include_router(actions_router)
router.include_router(profile_router)

# ── Phase 5: People Intelligence ──────────────────────────────────────────────
router.include_router(contacts_router)

# ── Phase 8: Email Automation ──────────────────────────────────────────────────
router.include_router(outreach_router)

from app.api.v1.analytics import router as analytics_router
from app.api.v1.agents import router as agents_router

# ── Phase 9: Analytics + Agent Status ─────────────────────────────────────────
router.include_router(analytics_router)
router.include_router(agents_router)
