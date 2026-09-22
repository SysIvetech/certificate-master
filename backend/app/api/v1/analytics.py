"""학습 분석 API 엔드포인트.

복합 진행도 지표, 학습 패턴 분석, 이탈 위험 감지 기능을 제공합니다.
MariaDB (SQLAlchemy)로 마이그레이션됨.
"""

import logging
from datetime import date

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DBSession
from app.models.checkin import Checkin as CheckinModel
from app.models.study_plan import StudyPlan as StudyPlanModel
from app.schemas.analytics import LearningPattern, ProgressAnalytics
from app.services.analytics_service import AnalyticsService
from app.services.learning_pattern_service import LearningPatternService

router = APIRouter()
logger = logging.getLogger(__name__)
analytics_service = AnalyticsService()
learning_pattern_service = LearningPatternService()


@router.get("/progress/{study_plan_id}", response_model=ProgressAnalytics)
async def get_progress_analytics(
    study_plan_id: str,
    db: DBSession,
    user: CurrentUser,
):
    """복합 진행도 분석 조회.

    학습 계획의 복합 진행도 지표를 제공합니다.
    진도율, 시간 이행률, 일정 준수율, 학습 연속성, 이탈 위험 신호 등을 포함합니다.

    Args:
        study_plan_id: 학습 계획 UUID

    Returns:
        ProgressAnalytics: 복합 진행도 분석 결과.

    Raises:
        HTTPException: 404 - 학습 계획을 찾을 수 없음 또는 접근 권한 없음.
    """
    # 1. 학습 계획 조회
    study_plan = (
        db.query(StudyPlanModel)
        .filter(StudyPlanModel.id == study_plan_id)
        .filter(StudyPlanModel.user_id == user.id)
        .first()
    )

    if not study_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan with id {study_plan_id} not found",
        )

    plan = study_plan.to_dict()

    # 2. 체크인 데이터 조회
    checkins_query = (
        db.query(CheckinModel)
        .filter(CheckinModel.study_plan_id == study_plan_id)
        .filter(CheckinModel.user_id == user.id)
        .order_by(CheckinModel.checkin_date.asc())
        .all()
    )

    checkins = [c.to_dict() for c in checkins_query]

    # 3. 지표 계산
    milestones = plan.get("milestones", [])
    completion_rate = analytics_service.calculate_completion_rate(milestones)

    # 시간 이행률
    daily_planned_hours = plan.get("daily_study_hours", 2.0)
    total_planned_hours = (
        daily_planned_hours * len(checkins) if checkins else daily_planned_hours
    )
    total_actual_hours = sum(c.get("hours_studied", 0) for c in checkins)
    time_adherence_rate = analytics_service.calculate_time_adherence_rate(
        total_planned_hours, total_actual_hours
    )

    # 일정 준수율
    target_date_str = plan["target_date"]
    if isinstance(target_date_str, str):
        target_date = date.fromisoformat(target_date_str)
    else:
        target_date = target_date_str

    created_at_str = plan["created_at"]
    if isinstance(created_at_str, str):
        start_date = date.fromisoformat(created_at_str.split("T")[0])
    else:
        start_date = (
            created_at_str.date() if hasattr(created_at_str, "date") else created_at_str
        )

    current_progress = plan.get("progress_percentage", completion_rate)
    schedule_adherence_rate = analytics_service.calculate_schedule_adherence_rate(
        start_date, target_date, current_progress
    )

    # 연속 학습일 (체크인 API에서 가져오기)
    from app.api.v1.checkins import get_checkin_stats

    stats_response = await get_checkin_stats(
        db=db,
        user=user,
        study_plan_id=study_plan_id,
    )
    current_streak = stats_response.current_streak

    # 4. 위험 신호 감지
    risk_signals = []

    if checkins:
        last_checkin_date_str = checkins[-1]["checkin_date"]
        if isinstance(last_checkin_date_str, str):
            last_checkin_date = date.fromisoformat(last_checkin_date_str)
        else:
            last_checkin_date = last_checkin_date_str
        risk_signals.extend(analytics_service.detect_streak_broken(last_checkin_date))

        # 최근 7일 평균 학습 시간
        recent_checkins = checkins[-7:] if len(checkins) >= 7 else checkins
        recent_avg_hours = (
            sum(c.get("hours_studied", 0) for c in recent_checkins)
            / len(recent_checkins)
            if recent_checkins
            else 0
        )
        risk_signals.extend(
            analytics_service.detect_time_decreased(
                daily_planned_hours, recent_avg_hours
            )
        )

        # 기분 추이
        recent_moods = [c.get("mood") for c in checkins[-7:] if c.get("mood")]
        risk_signals.extend(analytics_service.detect_mood_deteriorated(recent_moods))

    # 5. 학습자 상태 분류
    learner_status = analytics_service.classify_learner_status(
        schedule_adherence_rate, current_streak
    )

    # 6. 복습 긴급도
    if checkins:
        last_date_str = checkins[-1]["checkin_date"]
        if isinstance(last_date_str, str):
            last_date = date.fromisoformat(last_date_str)
        else:
            last_date = last_date_str
        days_since_last_checkin = (date.today() - last_date).days
    else:
        days_since_last_checkin = 999
    review_urgency = analytics_service.calculate_review_urgency(days_since_last_checkin)

    # 7. 완료일 예측
    if checkins and len(checkins) >= 3:
        # 최근 7일 평균 진도율 증가량
        recent_progress_increase = current_progress / len(checkins) if checkins else 0
        predicted_completion_date = analytics_service.predict_completion_date(
            target_date, current_progress, recent_progress_increase
        )
    else:
        predicted_completion_date = target_date

    # 8. 추천 액션
    recommendations = analytics_service.generate_recommendations(
        learner_status,
        schedule_adherence_rate,
        time_adherence_rate,
        risk_signals,
    )

    # 9. 응답 구성
    return ProgressAnalytics(
        plan_id=study_plan_id,
        completion_rate=completion_rate,
        time_adherence_rate=time_adherence_rate,
        schedule_adherence_rate=schedule_adherence_rate,
        current_streak=current_streak,
        learning_pattern_score=0.0,  # 향후 구현
        review_urgency=review_urgency,
        status=learner_status,
        predicted_completion_date=predicted_completion_date,
        recommendations=recommendations,
        risk_signals=risk_signals,
    )


@router.get("/learning-pattern/{study_plan_id}", response_model=LearningPattern)
async def get_learning_pattern(
    study_plan_id: str,
    db: DBSession,
    user: CurrentUser,
):
    """학습 패턴 분석 조회.

    학습자의 학습 패턴을 분석하여 제공합니다.
    선호 학습 시간대, 요일별 효율, 기분 추이, 학습 일관성 등을 포함합니다.

    Args:
        study_plan_id: 학습 계획 UUID

    Returns:
        LearningPattern: 학습 패턴 분석 결과.

    Raises:
        HTTPException: 404 - 학습 계획을 찾을 수 없음 또는 접근 권한 없음.
        HTTPException: 400 - 분석에 필요한 데이터가 부족함 (체크인 3개 미만).
    """
    # 1. 학습 계획 조회
    study_plan = (
        db.query(StudyPlanModel)
        .filter(StudyPlanModel.id == study_plan_id)
        .filter(StudyPlanModel.user_id == user.id)
        .first()
    )

    if not study_plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study plan with id {study_plan_id} not found",
        )

    # 2. 체크인 데이터 조회
    checkins_query = (
        db.query(CheckinModel)
        .filter(CheckinModel.study_plan_id == study_plan_id)
        .filter(CheckinModel.user_id == user.id)
        .order_by(CheckinModel.checkin_date.asc())
        .all()
    )

    checkins = [c.to_dict() for c in checkins_query]

    # 3. 최소 데이터 요구사항 확인
    if len(checkins) < 3:
        # 데이터가 부족하면 기본값 반환
        return LearningPattern(
            plan_id=study_plan_id,
            preferred_time_slots=[],
            average_session_duration=0.0,
            best_weekday=None,
            worst_weekday=None,
            mood_trend="stable",
            recent_moods=[],
            consistency_score=0.0,
        )

    # 4. 학습 패턴 분석
    pattern_data = learning_pattern_service.analyze_learning_pattern(
        checkins, study_plan_id
    )

    # 5. 응답 구성
    return LearningPattern(**pattern_data)
