"""Pydantic schemas for StudyPlan model.

This module defines request/response schemas for study plan endpoints.
"""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class Milestone(BaseModel):
    """Schema for a study plan milestone."""

    week: int = Field(..., description="주차")
    title: str = Field(..., description="마일스톤 제목")
    description: str = Field(..., description="마일스톤 설명")
    hours: float = Field(..., description="예상 학습 시간")
    completed: bool = Field(False, description="완료 여부")


class StudyPlanBase(BaseModel):
    """Base schema for StudyPlan with common fields."""

    title: str = Field(..., description="학습 계획 제목")
    target_date: date = Field(..., description="목표 완료일")
    daily_study_hours: float = Field(2.0, ge=0.5, le=12.0, description="하루 학습 시간")


class StudyPlanCreate(StudyPlanBase):
    """Schema for creating a new study plan."""

    certificate_id: str = Field(..., description="자격증 UUID")
    topics: Optional[list[dict[str, Any]]] = Field(None, description="학습 주제 목록")
    milestones: Optional[list[dict[str, Any]]] = Field(
        None, description="AI 생성 마일스톤 (없으면 자동 생성)"
    )


class StudyPlanUpdate(BaseModel):
    """Schema for updating a study plan (partial update)."""

    title: Optional[str] = Field(None, description="학습 계획 제목")
    target_date: Optional[date] = Field(None, description="목표 완료일")
    daily_study_hours: Optional[float] = Field(
        None, ge=0.5, le=12.0, description="하루 학습 시간"
    )
    topics: Optional[list[dict[str, Any]]] = Field(None, description="학습 주제 목록")
    milestones: Optional[list[dict[str, Any]]] = Field(
        None, description="마일스톤 업데이트"
    )
    status: Optional[str] = Field(
        None, description="계획 상태 (active, completed, paused, cancelled)"
    )
    progress_percentage: Optional[float] = Field(
        None, ge=0.0, le=100.0, description="진행률 (%)"
    )
    total_weeks: Optional[int] = Field(None, ge=0, description="총 학습 주차 수")
    estimated_total_hours: Optional[float] = Field(
        None, ge=0.0, description="총 예상 학습 시간"
    )


class StudyPlan(StudyPlanBase):
    """Schema for study plan response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="UUID")
    user_id: str = Field(..., description="사용자 UUID")
    certificate_id: str = Field(..., description="자격증 UUID")

    topics: list[dict[str, Any]] = Field(
        default_factory=list, description="학습 주제 목록"
    )
    milestones: list[dict[str, Any]] = Field(
        default_factory=list, description="마일스톤 목록"
    )
    status: str = Field("active", description="계획 상태")
    progress_percentage: float = Field(0.0, description="진행률 (%)")
    total_weeks: Optional[int] = Field(None, description="총 학습 주차 수")
    estimated_total_hours: Optional[float] = Field(
        None, description="총 예상 학습 시간"
    )

    created_at: datetime
    updated_at: datetime


class StudyPlanList(BaseModel):
    """Schema for paginated study plan list response."""

    items: list[StudyPlan]
    total: int
