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

# ── Remaining routers ─────────────────────────────────────────────────────────
# TODO: include outreach router      (Phase 8)
# TODO: include agents router        (Phase 2)
# TODO: include analytics router     (Phase 4)
