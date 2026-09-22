"""
Progress Analytics API Endpoints

Provides velocity metrics, progress predictions, and analytics
for study plans.

MariaDB(SQLAlchemy)로 마이그레이션됨 (2026-01-22).
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DBSession
from app.models.study_plan import StudyPlan
from app.services.velocity_calculator import VelocityCalculator

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{plan_id}/velocity")
async def get_velocity_metrics(
    plan_id: str,
    user: CurrentUser,
    db: DBSession,
):
    """
    Get velocity and prediction metrics for a study plan.

    Args:
        plan_id: Study plan UUID
        user: Current authenticated user
        db: SQLAlchemy 데이터베이스 세션

    Returns:
        VelocityMetrics response with:
        - expected_progress: Expected progress % based on timeline
        - actual_progress: Actual progress % from milestones
        - progress_delta: Difference (actual - expected)
        - velocity: Progress rate in %/day
        - predicted_date: ISO date string for predicted completion
        - status: 'ahead' | 'on-track' | 'behind' | 'critical'

    Raises:
        HTTPException 404: Study plan not found
        HTTPException 403: User doesn't own this plan
    """
    # Fetch study plan using SQLAlchemy
    study_plan_model = (
        db.query(StudyPlan)
        .filter(StudyPlan.id == plan_id)
        .filter(StudyPlan.user_id == user.id)
        .first()
    )

    if not study_plan_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Study plan not found or you don't have access",
        )

    study_plan = study_plan_model.to_dict()

    # Fetch progress snapshots (last 30 days for velocity calculation)
    # Note: progress_snapshots 테이블/모델은 아직 구현되지 않음
    # 현재는 빈 스냅샷으로 동작 (velocity will be 0)
    snapshots = []

    # Calculate velocity metrics
    calculator = VelocityCalculator(study_plan, snapshots)
    velocity_status = calculator.get_velocity_status()

    return velocity_status
