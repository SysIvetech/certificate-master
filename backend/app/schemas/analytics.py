"""학습 분석 스키마.

복합 진행도 지표 및 학습 패턴 분석 관련 Pydantic 모델을 정의합니다.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LearnerStatus(str, Enum):
    """학습자 상태 분류."""

    EXCEEDING = "exceeding"  # 초과 달성 (진도 > 120%)
    ON_TRACK = "on_track"  # 정상 진행 (80% ≤ 진도 ≤ 120%)
    NEEDS_ATTENTION = "needs_attention"  # 주의 필요 (50% ≤ 진도 < 80%)
    AT_RISK = "at_risk"  # 이탈 위험 (진도 < 50% 또는 연속성 = 0)


class ReviewUrgency(str, Enum):
    """복습 긴급도."""

    LOW = "low"  # 최근 7일 이내 복습
    MEDIUM = "medium"  # 7-14일 전 복습
    HIGH = "high"  # 14일 이상 복습 안함


class RiskSignalType(str, Enum):
    """이탈 위험 신호 유형."""

    STREAK_BROKEN = "streak_broken"  # 연속성 단절
    TIME_DECREASED = "time_decreased"  # 학습 시간 급감
    MOOD_DETERIORATED = "mood_deteriorated"  # 기분 악화
    MILESTONE_DELAYED = "milestone_delayed"  # 마일스톤 지연


class RiskSignal(BaseModel):
    """이탈 위험 신호."""

    type: RiskSignalType = Field(..., description="위험 유형")
    severity: str = Field(..., description="심각도 (low, medium, high)")
    description: str = Field(..., description="상세 설명")
    detected_at: datetime = Field(default_factory=datetime.now, description="감지 시각")


class ProgressAnalytics(BaseModel):
    """복합 진행도 분석 결과."""

    plan_id: str = Field(..., description="학습 계획 UUID")

    # 핵심 지표
    completion_rate: float = Field(..., ge=0.0, le=100.0, description="진도율 (%)")
    time_adherence_rate: float = Field(..., ge=0.0, description="시간 이행률 (%)")
    schedule_adherence_rate: float = Field(..., ge=0.0, description="일정 준수율 (%)")
    current_streak: int = Field(..., ge=0, description="현재 연속 학습일")

    # 추가 지표
    learning_pattern_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="학습 패턴 점수"
    )
    review_urgency: ReviewUrgency = Field(
        default=ReviewUrgency.LOW, description="복습 긴급도"
    )

    # 상태 및 예측
    status: LearnerStatus = Field(..., description="학습자 상태")
    predicted_completion_date: Optional[date] = Field(None, description="예상 완료일")

    # 추천 액션
    recommendations: list[str] = Field(
        default_factory=list, description="추천 액션 목록"
    )
    risk_signals: list[RiskSignal] = Field(
        default_factory=list, description="이탈 위험 신호"
    )


class LearningPattern(BaseModel):
    """학습 패턴 분석 결과."""

    plan_id: str = Field(..., description="학습 계획 UUID")

    # 시간대 분석
    preferred_time_slots: list[str] = Field(
        default_factory=list, description="선호 학습 시간대 (예: 오전, 오후, 저녁)"
    )
    average_session_duration: float = Field(
        0.0, description="평균 학습 세션 시간 (시간)"
    )

    # 요일별 효율
    best_weekday: Optional[str] = Field(None, description="가장 효율적인 요일")
    worst_weekday: Optional[str] = Field(None, description="가장 비효율적인 요일")

    # 기분 추이
    mood_trend: str = Field(
        default="stable", description="기분 추이 (improving, stable, declining)"
    )
    recent_moods: list[str] = Field(
        default_factory=list, description="최근 7일 기분 기록"
    )

    # 학습 일관성
    consistency_score: float = Field(
        0.0, ge=0.0, le=100.0, description="학습 일관성 점수"
    )


class AdminStats(BaseModel):
    """관리자 대시보드 통계."""

    total_learners: int = Field(..., description="전체 학습자 수")
    active_learners: int = Field(..., description="활성 학습자 수 (최근 7일 활동)")

    # 상태별 분류
    exceeding_count: int = Field(0, description="초과 달성 학습자 수")
    on_track_count: int = Field(0, description="정상 진행 학습자 수")
    needs_attention_count: int = Field(0, description="주의 필요 학습자 수")
    at_risk_count: int = Field(0, description="이탈 위험 학습자 수")

    # 평균 지표
    average_completion_rate: float = Field(0.0, description="평균 진도율 (%)")
    average_streak: float = Field(0.0, description="평균 연속 학습일")

    # 이탈률
    churn_rate: float = Field(0.0, ge=0.0, le=100.0, description="이탈률 (%)")


class AtRiskLearner(BaseModel):
    """이탈 위험 학습자 정보."""

    user_id: str = Field(..., description="사용자 UUID")
    plan_id: str = Field(..., description="학습 계획 UUID")
    certificate_title: str = Field(..., description="자격증 명")

    risk_signals: list[RiskSignal] = Field(..., description="감지된 위험 신호")
    days_since_last_checkin: int = Field(..., description="마지막 체크인 이후 일수")
    schedule_adherence_rate: float = Field(..., description="일정 준수율 (%)")
