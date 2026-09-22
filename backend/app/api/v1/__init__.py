"""API v1 module.

This module exports the main API router for version 1.
"""

from fastapi import APIRouter

from .analytics import router as analytics_router
from .certificates import router as certificates_router
from .checkins import router as checkins_router
from .progress_analytics import router as progress_analytics_router
from .recommendations import router as recommendations_router
from .study_plans import router as study_plans_router

router = APIRouter(prefix="/v1")

# Include all routers
router.include_router(
    certificates_router, prefix="/certificates", tags=["certificates"]
)
router.include_router(study_plans_router, prefix="/study-plans", tags=["study-plans"])
router.include_router(checkins_router, prefix="/checkins", tags=["checkins"])
router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
router.include_router(
    progress_analytics_router, prefix="/progress-analytics", tags=["progress-analytics"]
)
router.include_router(
    recommendations_router, prefix="/recommendations", tags=["recommendations"]
)
