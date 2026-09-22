"""Pydantic schemas for Checkin model.

This module defines request/response schemas for checkin endpoints.
"""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

MoodType = Literal["great", "good", "okay", "tired", "stressed"]


class CheckinBase(BaseModel):
    """Base schema for Checkin with common fields."""

    hours_studied: float = Field(..., ge=0, le=24, description="학습 시간")
    notes: Optional[str] = Field(None, description="학습 메모")
    mood: Optional[MoodType] = Field(None, description="기분 상태")


class CheckinCreate(CheckinBase):
    """Schema for creating a new checkin."""

    study_plan_id: str = Field(..., description="학습 계획 UUID")
    checkin_date: Optional[date] = Field(None, description="체크인 날짜 (기본값: 오늘)")


class CheckinUpdate(BaseModel):
    """Schema for updating a checkin (partial update)."""

    hours_studied: Optional[float] = Field(None, ge=0, le=24, description="학습 시간")
    notes: Optional[str] = Field(None, description="학습 메모")
    mood: Optional[MoodType] = Field(None, description="기분 상태")


class Checkin(CheckinBase):
    """Schema for checkin response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="UUID")
    study_plan_id: str = Field(..., description="학습 계획 UUID")
    user_id: str = Field(..., description="사용자 UUID")
    checkin_date: date = Field(..., description="체크인 날짜")

    created_at: datetime


class CheckinList(BaseModel):
    """Schema for checkin list response."""

    items: list[Checkin]
    total: int


class CheckinStats(BaseModel):
    """Schema for checkin statistics."""

    total_hours: float = Field(..., description="총 학습 시간")
    total_days: int = Field(..., description="총 학습 일수")
    average_hours_per_day: float = Field(..., description="일평균 학습 시간")
    current_streak: int = Field(..., description="현재 연속 학습일")
    longest_streak: int = Field(..., description="최장 연속 학습일")
