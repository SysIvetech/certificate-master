"""학습 계획 API 엔드포인트.

사용자의 학습 계획 CRUD 기능을 제공합니다.
MariaDB (SQLAlchemy)로 마이그레이션됨.
"""

import logging
import math
import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, DBSession
from app.models.certificate import Certificate as CertificateModel
from app.models.study_plan import StudyPlan as StudyPlanModel
from app.schemas.study_plan import (
    StudyPlan,
    StudyPlanCreate,
    StudyPlanList,
    StudyPlanUpdate,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _calculate_progress_from_milestones(milestones: list[dict]) -> float:
    if not milestones:
        return 0.0
    completed = sum(1 for milestone in milestones if milestone.get("completed"))
    return round((completed / len(milestones)) * 100, 1)


def _calculate_total_weeks(target_date: date, milestones: list[dict]) -> int:
    if milestones:
        milestone_weeks = [
            milestone.get("week") for milestone in milestones if milestone.get("week")
        ]
        if milestone_weeks:
            return max(int(week) for week in milestone_weeks)
    days_remaining = (target_date - date.today()).days
    if days_remaining <= 0:
        return 0
    return math.ceil(days_remaining / 7)


def _calculate_estimated_total_hours(
    target_date: date,
    daily_study_hours: float,
    milestones: list[dict],
) -> float | None:
    if milestones:
        milestone_hours = [
            milestone.get("hours")
            for milestone in milestones
            if milestone.get("hours") is not None
        ]
        if milestone_hours:
            return round(sum(float(hours) for hours in milestone_hours), 1)
    days_remaining = (target_date - date.today()).days
    if days_remaining <= 0:
        return None
    return round(daily_study_hours * days_remaining, 1)


@router.get("/", response_model=StudyPlanList)
async def get_my_study_plans(
    db: DBSession,
    user: CurrentUser,
):
    """현재 사용자의 모든 학습 계획 조회.

    인증된 사용자의 모든 학습 계획을 최신순으로 반환합니다.

    Returns:
        StudyPlanList: 학습 계획 목록 및 총 개수.
    """
    query = (
        db.query(StudyPlanModel)
        .filter(StudyPlanModel.user_id == user.id)
        .order_by(StudyPlanModel.created_at.desc())
    )

    results = query.all()
    total = query.count()

    items = [StudyPlan.model_validate(item.to_dict()) for item in results]

    return StudyPlanList(items=items, total=total)


@router.post("/", response_model=StudyPlan, status_code=status.HTTP_201_CREATED)
async def create_study_plan(
    plan_data: StudyPlanCreate,
    request: Request,
    db: DBSession,
    user: CurrentUser,
):
    """새 학습 계획 생성 (LLM 기반 자동 생성).

    자격증 정보와 사용자 입력을 기반으로 LLM이 맞춤형 학습 계획을 자동 생성합니다.

    Args:
        plan_data: 학습 계획 생성 데이터 (자격증 ID, 제목, 목표일, 학습 시간 등)

    Returns:
        StudyPlan: 생성된 학습 계획 (LLM이 생성한 milestones와 topics 포함).

    Raises:
        HTTPException: 404 - 자격증을 찾을 수 없음, 500 - LLM 오류 또는 데이터베이스 오류.
    """
    # Verify certificate exists and fetch full data
    certificate = (
        db.query(CertificateModel)
        .filter(CertificateModel.id == plan_data.certificate_id)
        .first()
    )

    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with id {plan_data.certificate_id} not found",
        )

    certificate_data = certificate.to_dict()

    # Generate study plan using LLM (if milestones not provided)
    milestones_data = plan_data.milestones or []
    topics_data = plan_data.topics or []

    total_weeks = None
    estimated_total_hours = None

    if not milestones_data:  # LLM 자동 생성
        try:
            logger.info(
                f"Generating study plan with LLM for certificate: {certificate_data.get('title')}"
            )

            from app.services.study_plan_service import get_study_plan_service

            study_plan_service = get_study_plan_service()
            generated_plan = await study_plan_service.generate_study_plan(
                certificate_data=certificate_data,
                target_date=plan_data.target_date,
                daily_study_hours=plan_data.daily_study_hours,
            )

            # Convert Pydantic models to dicts
            milestones_data = [
                milestone.model_dump() for milestone in generated_plan.milestones
            ]
            topics_data = [topic.model_dump() for topic in generated_plan.topics]
            total_weeks = generated_plan.total_weeks
            estimated_total_hours = generated_plan.estimated_total_hours

            logger.info(
                f"Generated {len(milestones_data)} milestones and {len(topics_data)} topics"
            )
        except ValueError as e:
            logger.error(f"LLM generation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate study plan: {str(e)}",
            )
        except Exception as e:
            logger.error(f"Unexpected error during LLM generation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unexpected error: {str(e)}",
            )

    # Create study plan
    if total_weeks is None:
        total_weeks = _calculate_total_weeks(plan_data.target_date, milestones_data)
    if estimated_total_hours is None:
        estimated_total_hours = _calculate_estimated_total_hours(
            plan_data.target_date,
            plan_data.daily_study_hours,
            milestones_data,
        )

    study_plan = StudyPlanModel(
        id=str(uuid.uuid4()),
        user_id=user.id,
        certificate_id=plan_data.certificate_id,
        title=plan_data.title,
        target_date=plan_data.target_date,
        daily_study_hours=plan_data.daily_study_hours,
        topics=topics_data,
        milestones=milestones_data,
        progress_percentage=0.0,
        total_weeks=total_weeks,
        estimated_total_hours=estimated_total_hours,
    )

    db.add(study_plan)
    db.commit()
    db.refresh(study_plan)

    return StudyPlan.model_validate(study_plan.to_dict())


@router.get("/{plan_id}", response_model=StudyPlan)
async def get_study_plan(
    plan_id: str,
    db: DBSession,
    user: CurrentUser,
):
    """특정 학습 계획 조회.

    UUID로 학습 계획을 조회합니다. 자신의 계획만 조회 가능합니다.

    Args:
        plan_id: 학습 계획 UUID

    Returns:
        StudyPlan: 학습 계획 상세 정보.

    Raises:
        HTTPException: 404 - 계획을 찾을 수 없음 또는 접근 권한 없음.
    """
    study_plan = (
        db.query(StudyPlanModel)
        .filter(StudyPlanModel.id == plan_id)
        .filter(StudyPlanModel.user_id == user.id)
        .first()
    )

    if not study_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan with id {plan_id} not found",
        )

    return StudyPlan.model_validate(study_plan.to_dict())


@router.patch("/{plan_id}", response_model=StudyPlan)
async def update_study_plan(
    plan_id: str,
    update_data: StudyPlanUpdate,
    db: DBSession,
    user: CurrentUser,
):
    """학습 계획 업데이트 (부분 업데이트 지원).

    학습 계획의 특정 필드만 업데이트할 수 있습니다.

    Args:
        plan_id: 학습 계획 UUID
        update_data: 업데이트할 필드

    Returns:
        StudyPlan: 업데이트된 학습 계획.

    Raises:
        HTTPException: 400 - 업데이트할 필드 없음, 404 - 계획을 찾을 수 없음.
    """
    study_plan = (
        db.query(StudyPlanModel)
        .filter(StudyPlanModel.id == plan_id)
        .filter(StudyPlanModel.user_id == user.id)
        .first()
    )

    if not study_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan with id {plan_id} not found",
        )

    # Build update dict
    update_dict = {}
    if update_data.title is not None:
        update_dict["title"] = update_data.title
    if update_data.target_date is not None:
        update_dict["target_date"] = update_data.target_date
    if update_data.daily_study_hours is not None:
        update_dict["daily_study_hours"] = update_data.daily_study_hours
    if update_data.topics is not None:
        update_dict["topics"] = update_data.topics
    if update_data.milestones is not None:
        update_dict["milestones"] = update_data.milestones
        if update_data.progress_percentage is None:
            update_dict["progress_percentage"] = _calculate_progress_from_milestones(
                update_data.milestones
            )
    if update_data.status is not None:
        update_dict["status"] = update_data.status
    if update_data.progress_percentage is not None:
        update_dict["progress_percentage"] = update_data.progress_percentage
    if update_data.total_weeks is not None:
        update_dict["total_weeks"] = update_data.total_weeks
    if update_data.estimated_total_hours is not None:
        update_dict["estimated_total_hours"] = update_data.estimated_total_hours
    if update_dict.get("progress_percentage", 0) >= 100:
        update_dict["status"] = "completed"

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    # Update fields
    for key, value in update_dict.items():
        setattr(study_plan, key, value)

    db.commit()
    db.refresh(study_plan)

    return StudyPlan.model_validate(study_plan.to_dict())


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_study_plan(
    plan_id: str,
    db: DBSession,
    user: CurrentUser,
):
    """학습 계획 삭제.

    학습 계획을 삭제합니다. 관련된 체크인도 함께 삭제됩니다 (CASCADE).

    Args:
        plan_id: 학습 계획 UUID

    Raises:
        HTTPException: 404 - 계획을 찾을 수 없음 또는 접근 권한 없음.
    """
    study_plan = (
        db.query(StudyPlanModel)
        .filter(StudyPlanModel.id == plan_id)
        .filter(StudyPlanModel.user_id == user.id)
        .first()
    )

    if not study_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan with id {plan_id} not found",
        )

    db.delete(study_plan)
    db.commit()
