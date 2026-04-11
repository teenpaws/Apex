"""
API v1 aggregate router.

All sub-routers for v1 are registered here. Phase 1 includes only the
health router. Remaining routers are added in subsequent phases.
"""

from fastapi import APIRouter

from app.api.v1.health import router as health_router

router = APIRouter()

# ── Phase 1: Infrastructure ────────────────────────────────────────────────────
router.include_router(health_router)

# ── Phase 2+: Feature routers (uncomment as implemented) ──────────────────────
# TODO: include signals router       (Phase 2)
# TODO: include opportunities router (Phase 2)
# TODO: include actions router       (Phase 2)
# TODO: include profile router       (Phase 2)
# TODO: include outreach router      (Phase 3)
# TODO: include auth router          (Phase 2)
# TODO: include companies router     (Phase 2)
# TODO: include contacts router      (Phase 3)
# TODO: include agents router        (Phase 2)
# TODO: include analytics router     (Phase 4)
