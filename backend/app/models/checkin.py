"""Checkin 모델.

학습 체크인 정보를 저장하는 테이블의 ORM 모델.
"""

import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class Checkin(Base):
    """학습 체크인 모델.

    Attributes:
        id: 고유 식별자 (UUID)
        user_id: 사용자 ID
        study_plan_id: 학습 계획 ID (FK)
        checkin_date: 체크인 날짜
        hours_studied: 학습한 시간
        completed_topics: 완료한 주제 목록 (JSON)
        notes: 메모
        mood: 기분 (good, normal, bad 등)
        created_at: 생성 시간
    """

    __tablename__ = "checkins"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    study_plan_id = Column(
        String(36),
        ForeignKey("study_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    checkin_date = Column(Date, nullable=False)
    hours_studied = Column(Float, nullable=False)
    completed_topics = Column(JSON, nullable=True, default=list)
    notes = Column(Text, nullable=True)
    mood = Column(String(20), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    study_plan = relationship("StudyPlan", back_populates="checkins")

    def __repr__(self) -> str:
        return f"<Checkin(id={self.id}, date={self.checkin_date})>"

    def to_dict(self) -> dict:
        """모델을 딕셔너리로 변환."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "study_plan_id": self.study_plan_id,
            "checkin_date": (
                self.checkin_date.isoformat() if self.checkin_date else None
            ),
            "hours_studied": self.hours_studied,
            "completed_topics": self.completed_topics,
            "notes": self.notes,
            "mood": self.mood,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
