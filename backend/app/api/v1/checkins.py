"""체크인 API 엔드포인트.

학습 체크인 CRUD 및 통계 기능을 제공합니다.
MariaDB (SQLAlchemy)로 마이그레이션됨.
"""

import logging
import uuid
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DBSession
from app.models.checkin import Checkin as CheckinModel
from app.models.study_plan import StudyPlan as StudyPlanModel
from app.schemas.checkin import (
    Checkin,
    CheckinCreate,
    CheckinList,
    CheckinStats,
    CheckinUpdate,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=CheckinList)
async def get_my_checkins(
    db: DBSession,
    user: CurrentUser,
    study_plan_id: Optional[str] = Query(None, description="학습 계획 ID로 필터"),
    start_date: Optional[date] = Query(None, description="시작 날짜"),
    end_date: Optional[date] = Query(None, description="종료 날짜"),
):
    """현재 사용자의 모든 체크인 조회 (필터링 지원).

    학습 계획, 날짜 범위로 필터링하여 체크인 기록을 조회합니다.

    Args:
        study_plan_id: 학습 계획 ID로 필터 (선택사항)
        start_date: 시작 날짜 (선택사항)
        end_date: 종료 날짜 (선택사항)

    Returns:
        CheckinList: 체크인 목록 및 총 개수 (최신순 정렬).
    """
    query = db.query(CheckinModel).filter(CheckinModel.user_id == user.id)

    if study_plan_id:
        query = query.filter(CheckinModel.study_plan_id == study_plan_id)

    if start_date:
        query = query.filter(CheckinModel.checkin_date >= start_date)

    if end_date:
        query = query.filter(CheckinModel.checkin_date <= end_date)

    total = query.count()
    results = query.order_by(CheckinModel.checkin_date.desc()).all()

    items = [Checkin.model_validate(item.to_dict()) for item in results]

    return CheckinList(items=items, total=total)


@router.post("/", response_model=Checkin, status_code=status.HTTP_201_CREATED)
async def create_checkin(
    checkin_data: CheckinCreate,
    db: DBSession,
    user: CurrentUser,
):
    """새 체크인 생성.

    학습 계획에 대한 체크인을 생성합니다. 동일 날짜에 중복 생성 불가합니다.

    Args:
        checkin_data: 체크인 생성 데이터 (학습 시간, 메모, 기분 등)

    Returns:
        Checkin: 생성된 체크인.

    Raises:
        HTTPException: 404 - 학습 계획을 찾을 수 없음, 409 - 해당 날짜에 이미 체크인 존재.
    """
    # Verify study plan exists and belongs to user
    study_plan = (
        db.query(StudyPlanModel)
        .filter(StudyPlanModel.id == checkin_data.study_plan_id)
        .filter(StudyPlanModel.user_id == user.id)
        .first()
    )

    if not study_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan with id {checkin_data.study_plan_id} not found",
        )

    # Create checkin
    checkin_date = checkin_data.checkin_date or date.today()

    checkin = CheckinModel(
        id=str(uuid.uuid4()),
        user_id=user.id,
        study_plan_id=checkin_data.study_plan_id,
        checkin_date=checkin_date,
        hours_studied=checkin_data.hours_studied,
        notes=checkin_data.notes,
        mood=checkin_data.mood,
    )

    try:
        db.add(checkin)
        db.commit()
        db.refresh(checkin)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Checkin for {checkin_date} already exists for this study plan",
        )

    return Checkin.model_validate(checkin.to_dict())


@router.get("/stats", response_model=CheckinStats)
async def get_checkin_stats(
    db: DBSession,
    user: CurrentUser,
    study_plan_id: Optional[str] = Query(None, description="학습 계획 ID로 필터"),
):
    """체크인 통계 조회.

    총 학습 시간, 연속 학습일, 평균 학습 시간 등의 통계를 제공합니다.

    Args:
        study_plan_id: 학습 계획 ID로 필터 (선택사항)

    Returns:
        CheckinStats: 총 시간, 학습일수, 평균, 현재 연속일, 최장 연속일.
    """
    query = db.query(CheckinModel).filter(CheckinModel.user_id == user.id)

    if study_plan_id:
        query = query.filter(CheckinModel.study_plan_id == study_plan_id)

    checkins = query.order_by(CheckinModel.checkin_date.desc()).all()

    if not checkins:
        return CheckinStats(
            total_hours=0,
            total_days=0,
            average_hours_per_day=0,
            current_streak=0,
            longest_streak=0,
        )

    # Calculate stats
    total_hours = sum(float(c.hours_studied) for c in checkins)
    total_days = len(checkins)
    average_hours = total_hours / total_days if total_days > 0 else 0

    # Calculate streaks
    dates = sorted([c.checkin_date for c in checkins], reverse=True)

    current_streak = 0
    longest_streak = 0
    temp_streak = 1

    today = date.today()

    # Check if the most recent checkin is today or yesterday
    yesterday = today - timedelta(days=1)
    if dates and (dates[0] == today or dates[0] == yesterday):
        current_streak = 1

    for i in range(len(dates) - 1):
        diff = (dates[i] - dates[i + 1]).days
        if diff == 1:
            temp_streak += 1
            if i == 0 or (i > 0 and current_streak > 0):
                current_streak = temp_streak
        else:
            longest_streak = max(longest_streak, temp_streak)
            temp_streak = 1

    longest_streak = max(longest_streak, temp_streak, current_streak)

    return CheckinStats(
        total_hours=round(total_hours, 1),
        total_days=total_days,
        average_hours_per_day=round(average_hours, 1),
        current_streak=current_streak,
        longest_streak=longest_streak,
    )


@router.get("/{checkin_id}", response_model=Checkin)
async def get_checkin(
    checkin_id: str,
    db: DBSession,
    user: CurrentUser,
):
    """특정 체크인 조회.

    UUID로 체크인을 조회합니다. 자신의 체크인만 조회 가능합니다.

    Args:
        checkin_id: 체크인 UUID

    Returns:
        Checkin: 체크인 상세 정보.

    Raises:
        HTTPException: 404 - 체크인을 찾을 수 없음 또는 접근 권한 없음.
    """
    checkin = (
        db.query(CheckinModel)
        .filter(CheckinModel.id == checkin_id)
        .filter(CheckinModel.user_id == user.id)
        .first()
    )

    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkin with id {checkin_id} not found",
        )

    return Checkin.model_validate(checkin.to_dict())


@router.patch("/{checkin_id}", response_model=Checkin)
async def update_checkin(
    checkin_id: str,
    update_data: CheckinUpdate,
    db: DBSession,
    user: CurrentUser,
):
    """체크인 업데이트 (부분 업데이트 지원).

    체크인의 특정 필드만 업데이트할 수 있습니다.

    Args:
        checkin_id: 체크인 UUID
        update_data: 업데이트할 필드 (학습 시간, 메모, 기분)

    Returns:
        Checkin: 업데이트된 체크인.

    Raises:
        HTTPException: 400 - 업데이트할 필드 없음, 404 - 체크인을 찾을 수 없음.
    """
    checkin = (
        db.query(CheckinModel)
        .filter(CheckinModel.id == checkin_id)
        .filter(CheckinModel.user_id == user.id)
        .first()
    )

    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkin with id {checkin_id} not found",
        )

    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}

    if not update_dict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    # Update fields
    for key, value in update_dict.items():
        setattr(checkin, key, value)

    db.commit()
    db.refresh(checkin)

    return Checkin.model_validate(checkin.to_dict())


@router.delete("/{checkin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_checkin(
    checkin_id: str,
    db: DBSession,
    user: CurrentUser,
):
    """체크인 삭제.

    체크인을 삭제합니다.

    Args:
        checkin_id: 체크인 UUID

    Raises:
        HTTPException: 404 - 체크인을 찾을 수 없음 또는 접근 권한 없음.
    """
    checkin = (
        db.query(CheckinModel)
        .filter(CheckinModel.id == checkin_id)
        .filter(CheckinModel.user_id == user.id)
        .first()
    )

    if not checkin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checkin with id {checkin_id} not found",
        )

    db.delete(checkin)
    db.commit()
