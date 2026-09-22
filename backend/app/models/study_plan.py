"""StudyPlan 모델.

학습 계획 정보를 저장하는 테이블의 ORM 모델.
"""

import uuid

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.mysql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.base import Base


class StudyPlan(Base):
    """학습 계획 모델.

    Attributes:
        id: 고유 식별자 (UUID)
        user_id: 사용자 ID
        certificate_id: 자격증 ID (FK)
        title: 학습 계획 제목
        target_date: 목표 시험 일자
        daily_study_hours: 일일 학습 시간
        status: 상태 (active, completed, paused)
        progress_percentage: 진행률 (0-100)
        total_weeks: 총 학습 주차
        estimated_total_hours: 예상 총 학습 시간
        topics: 학습 주제 목록 (JSON)
        milestones: 마일스톤 목록 (JSON)
        created_at: 생성 시간
        updated_at: 수정 시간
    """

    __tablename__ = "study_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=False, index=True)
    certificate_id = Column(
        String(36),
        ForeignKey("certificates.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = Column(String(300), nullable=False)
    target_date = Column(Date, nullable=False)
    daily_study_hours = Column(Float, default=2.0)
    status = Column(String(20), default="active")
    progress_percentage = Column(Float, default=0.0)
    total_weeks = Column(Integer, nullable=True)
    estimated_total_hours = Column(Float, nullable=True)
    topics = Column(JSON, nullable=True, default=list)
    milestones = Column(JSON, nullable=True, default=list)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    certificate = relationship("Certificate", back_populates="study_plans")
    checkins = relationship("Checkin", back_populates="study_plan")

    def __repr__(self) -> str:
        return f"<StudyPlan(id={self.id}, title={self.title})>"

    def to_dict(self) -> dict:
        """모델을 딕셔너리로 변환.

        None 값은 Pydantic 스키마의 기본값으로 대체됩니다.
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "certificate_id": self.certificate_id,
            "title": self.title,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "daily_study_hours": self.daily_study_hours or 2.0,
            "status": self.status or "active",
            "progress_percentage": self.progress_percentage or 0.0,
            "total_weeks": self.total_weeks,
            "estimated_total_hours": self.estimated_total_hours,
            # JSON 필드들: None이면 기본값 사용
            "topics": self.topics or [],
            "milestones": self.milestones or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
