"""Pydantic schemas for Certificate model.

This module defines request/response schemas for certificate endpoints.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryInfo(BaseModel):
    """카테고리 정보 (M:N 관계 지원)."""

    code: str = Field(..., description="자격구분코드 (S, T, Q, W)")
    name: str = Field(..., description="자격구분명 (국가전문자격, 국가기술자격 등)")


class CertificateBase(BaseModel):
    """Base schema for Certificate with common fields."""

    categories: list[CategoryInfo] = Field(
        ..., description="자격증이 속한 카테고리 목록"
    )
    series: Optional[str] = Field(None, description="계열명")
    title: str = Field(..., description="종목명 (자격증 이름)")


class AutocompleteResult(BaseModel):
    """Schema for autocomplete results."""

    id: str = Field(..., description="자격증 ID")
    title: str = Field(..., description="자격증 제목")
    categories: list[CategoryInfo] = Field(
        ..., description="자격증이 속한 카테고리 목록"
    )
    series: Optional[str] = Field(None, description="계열명")


class SeriesByCategory(BaseModel):
    """Schema for series grouped by category."""

    category_name: str = Field(..., description="자격구분명")
    category_code: str = Field(..., description="자격구분코드")
    series: list[str] = Field(..., description="계열 목록")


class CertificateCreate(CertificateBase):
    """Schema for creating a new certificate."""

    raw_id: str = Field(..., description="고유 식별자 (code_title 형식)")


# ExamSchedule and Eligibility models removed - users should check official sources


class CareerInfo(BaseModel):
    """진로 및 활용 정보."""

    use_cases: list[str] = Field(default_factory=list, description="활용 분야")
    related_jobs: list[str] = Field(default_factory=list, description="관련 직업")
    average_salary: Optional[str] = Field(None, description="평균 연봉")
    job_prospects: Optional[str] = Field(None, description="취업 전망")
    industry: list[str] = Field(default_factory=list, description="관련 산업")


class UserReviews(BaseModel):
    """실제 후기 요약."""

    summary: Optional[str] = Field(None, description="전체 요약")
    difficulty_feedback: Optional[str] = Field(None, description="난이도 평가")
    study_tips: list[str] = Field(default_factory=list, description="학습 팁")
    common_challenges: list[str] = Field(
        default_factory=list, description="공통 어려움"
    )


class OfficialSources(BaseModel):
    """공식 출처 정보."""

    official_site: Optional[str] = Field(None, description="공식 사이트")
    issuing_organization: Optional[str] = Field(None, description="발급 기관")
    reference_urls: list[str] = Field(default_factory=list, description="참고 링크")


class TimeAllocation(BaseModel):
    """학습 시간 배분 정보."""

    theory: Optional[str] = Field(None, description="이론 학습 비율 (예: 40%)")
    practice: Optional[str] = Field(None, description="실전 문제 비율 (예: 50%)")
    review: Optional[str] = Field(None, description="복습 비율 (예: 10%)")


class RecommendedBook(BaseModel):
    """추천 교재 정보."""

    title: str = Field(..., description="교재명")
    publisher: Optional[str] = Field(None, description="출판사")
    type: Optional[str] = Field(None, description="교재 유형 (필기/실기/종합)")
    description: Optional[str] = Field(None, description="교재 설명")


class KeyExamTopic(BaseModel):
    """핵심 출제 토픽 정보."""

    topic: str = Field(..., description="토픽명")
    frequency: str = Field(
        ..., description="출제 빈도 ('매우 자주', '자주', '보통', '가끔')"
    )
    importance: str = Field(..., description="중요도 ('상', '중', '하')")
    description: Optional[str] = Field(None, description="토픽 상세 설명")


class StudyGuide(BaseModel):
    """학습 가이드 정보."""

    study_methods: list[str] = Field(
        default_factory=list,
        description="추천 공부 방법 (예: 교재 중심, 기출문제 위주)",
    )
    key_exam_topics: list[dict[str, Any]] = Field(
        default_factory=list, description="핵심 출제 토픽 목록 (KeyExamTopic 구조)"
    )
    time_allocation: Optional[dict[str, str]] = Field(
        None, description="시간 배분 가이드 (TimeAllocation 구조)"
    )
    recommended_books: list[dict[str, Any]] = Field(
        default_factory=list, description="추천 교재 목록 (RecommendedBook 구조)"
    )
    success_tips: list[str] = Field(
        default_factory=list, description="합격을 위한 핵심 팁"
    )


# ============================================================
# 취업준비생 관점 스키마 (NEW: 2026-01-28)
# ============================================================


class JobMarketInfo(BaseModel):
    """채용 시장 정보 - 취업에 도움되는지 판단용."""

    job_posting_frequency: Optional[str] = Field(
        None, description="채용공고 출현 빈도 ('매우 많음', '많음', '보통', '적음')"
    )
    preferred_industries: list[str] = Field(
        default_factory=list, description="선호 산업군 (예: ['IT', '금융', '제조'])"
    )
    requirement_type: Optional[str] = Field(
        None, description="채용 요건 유형 ('필수', '우대', '가산점')"
    )
    public_sector_points: Optional[str] = Field(
        None, description="공무원/공기업 가산점 (예: '5%', '3점')"
    )


class CostBreakdown(BaseModel):
    """비용 상세 - 총 취득 비용 투명화."""

    exam_fee: Optional[str] = Field(
        None, description="응시료 (예: '필기 19,400원 + 실기 22,600원')"
    )
    exam_fee_refund: Optional[str] = Field(None, description="환불 정책")
    textbook_cost: Optional[str] = Field(
        None, description="교재 비용 범위 (예: '30,000 ~ 50,000원')"
    )
    lecture_cost: Optional[str] = Field(
        None, description="인강 비용 범위 (예: '100,000 ~ 300,000원')"
    )
    free_resources: list[str] = Field(
        default_factory=list,
        description="무료 학습 자료 (예: ['큐넷 기출문제', '유튜브 무료 강의'])",
    )


class FeasibilityInfo(BaseModel):
    """합격 가능성 정보 - 비전공자/직장인 관점."""

    non_major_pass_rate: Optional[str] = Field(
        None, description="비전공자 합격률 추정 (예: '약 30-35%')"
    )
    self_study_possible: Optional[bool] = Field(None, description="독학 가능 여부")
    minimum_study_period: Optional[int] = Field(
        None, description="최소 합격 준비기간 (일)"
    )
    first_attempt_pass_rate: Optional[str] = Field(
        None, description="1회 합격 비율 (예: '약 40%')"
    )


class ExamScheduleDetail(BaseModel):
    """시험 일정 상세 - D-Day 계산용."""

    annual_exam_count: Optional[int] = Field(None, description="연간 시험 횟수")
    exam_type: Optional[str] = Field(
        None, description="시험 유형 ('CBT', '정기', 'CBT+정기')"
    )
    next_exam_date: Optional[str] = Field(None, description="다음 시험일 (예상)")
    registration_period: Optional[str] = Field(None, description="접수 기간")
    result_announcement: Optional[str] = Field(None, description="합격 발표일")


class SimilarCertificate(BaseModel):
    """유사 자격증 비교 정보."""

    certificate_id: Optional[str] = Field(None, description="유사 자격증 ID (있으면)")
    title: str = Field(..., description="유사 자격증명")
    comparison: Optional[str] = Field(
        None, description="비교 설명 (예: '기사보다 난이도 낮음')"
    )


class ExamInfo(BaseModel):
    """시험 정보 상세 구조."""

    subjects: list[str] = Field(default_factory=list, description="시험 과목")
    exam_type: str = Field(default="", description="시험 형식 (필기/실기/면접)")
    passing_criteria: str = Field(default="", description="합격 기준")
    total_fee: Optional[str] = Field(None, description="총 응시료 (원)")
    acquisition_method: Optional[str] = Field(
        None, description="취득 방법 (응시자격, 취득 절차)"
    )
    exam_criteria_url: Optional[str] = Field(None, description="출제 기준 링크")


class RecommendedLecture(BaseModel):
    """추천 강의 구조."""

    platform: str = Field(..., description="플랫폼명 (에듀윌, 해커스 등)")
    title: str = Field(..., description="강의명")
    url: str = Field(..., description="강의 링크")
    instructor: Optional[str] = Field(None, description="강사명")
    price: Optional[str] = Field(None, description="가격 (예: '150000원', '무료')")
    rating: Optional[float] = Field(None, ge=0, le=5, description="평점")
    review_count: Optional[int] = Field(None, ge=0, description="리뷰 수")
    relevance_score: float = Field(
        default=1.0, ge=0, le=1, description="관련성 점수 (LLM 평가)"
    )


class CertificateUpdate(BaseModel):
    """Schema for updating a certificate (partial update)."""

    model_config = ConfigDict(extra="forbid")

    # 벡터 ID (ChromaDB 동기화용)
    vector_id: Optional[str] = Field(None, description="ChromaDB 벡터 ID")

    # 필수 정보
    overview: Optional[str] = Field(None, description="자격증 개요 (3-5문장)")
    difficulty: Optional[int] = Field(None, ge=1, le=5, description="난이도 (1-5)")
    study_period_days: Optional[int] = Field(
        None, ge=1, description="권장 준비기간 (일)"
    )

    # 시험 정보
    exam_info: Optional[dict[str, Any]] = Field(
        None, description="시험 정보 (ExamInfo 구조)"
    )

    # 학습 & 강의
    recommended_lectures: Optional[list[dict[str, Any]]] = Field(
        None, description="추천 강의 목록 (RecommendedLecture 구조)"
    )

    # 진로 & 후기
    career_info: Optional[dict[str, Any]] = Field(
        None, description="진로 정보 (CareerInfo 구조)"
    )
    user_reviews: Optional[dict[str, Any]] = Field(
        None, description="후기 요약 (UserReviews 구조)"
    )

    # 공식 출처
    official_sources: Optional[dict[str, Any]] = Field(
        None, description="공식 출처 (OfficialSources 구조)"
    )

    # 학습 가이드
    study_guide: Optional[dict[str, Any]] = Field(
        None, description="학습 가이드 (StudyGuide 구조)"
    )

    # ============================================================
    # 취업준비생 관점 필드 (NEW: 2026-01-28)
    # ============================================================
    job_market_info: Optional[dict[str, Any]] = Field(
        None, description="채용 시장 정보 (JobMarketInfo 구조)"
    )
    cost_breakdown: Optional[dict[str, Any]] = Field(
        None, description="비용 상세 (CostBreakdown 구조)"
    )
    feasibility_info: Optional[dict[str, Any]] = Field(
        None, description="합격 가능성 정보 (FeasibilityInfo 구조)"
    )
    exam_schedule_detail: Optional[dict[str, Any]] = Field(
        None, description="시험 일정 상세 (ExamScheduleDetail 구조)"
    )
    similar_certificates: Optional[list[dict[str, Any]]] = Field(
        None, description="유사 자격증 비교 (SimilarCertificate 구조)"
    )


class Certificate(CertificateBase):
    """Schema for certificate response."""

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="UUID")
    raw_id: str = Field(..., description="고유 식별자")
    slug: str = Field(default="", description="URL용 슬러그")

    # 벡터 ID (ChromaDB 동기화용)
    vector_id: Optional[str] = Field(None, description="ChromaDB 벡터 ID")

    # 필수 정보
    overview: Optional[str] = Field(None, description="자격증 개요 (3-5문장)")
    difficulty: Optional[int] = Field(None, description="난이도 (1-5)")
    study_period_days: Optional[int] = Field(None, description="권장 준비기간 (일)")

    # 시험 정보
    exam_info: dict[str, Any] = Field(
        default_factory=dict, description="시험 정보 (ExamInfo 구조)"
    )

    # 학습 & 강의
    recommended_lectures: list[dict[str, Any]] = Field(
        default_factory=list, description="추천 강의 목록 (RecommendedLecture 구조)"
    )

    # 진로 & 후기
    career_info: dict[str, Any] = Field(
        default_factory=dict, description="진로 정보 (CareerInfo 구조)"
    )
    user_reviews: dict[str, Any] = Field(
        default_factory=dict, description="후기 요약 (UserReviews 구조)"
    )

    # 공식 출처
    official_sources: dict[str, Any] = Field(
        default_factory=dict, description="공식 출처 (OfficialSources 구조)"
    )

    # 학습 가이드
    study_guide: dict[str, Any] = Field(
        default_factory=dict, description="학습 가이드 (StudyGuide 구조)"
    )

    # ============================================================
    # 취업준비생 관점 필드 (NEW: 2026-01-28)
    # ============================================================
    job_market_info: dict[str, Any] = Field(
        default_factory=dict, description="채용 시장 정보 (JobMarketInfo 구조)"
    )
    cost_breakdown: dict[str, Any] = Field(
        default_factory=dict, description="비용 상세 (CostBreakdown 구조)"
    )
    feasibility_info: dict[str, Any] = Field(
        default_factory=dict, description="합격 가능성 정보 (FeasibilityInfo 구조)"
    )
    exam_schedule_detail: dict[str, Any] = Field(
        default_factory=dict, description="시험 일정 상세 (ExamScheduleDetail 구조)"
    )
    similar_certificates: list[dict[str, Any]] = Field(
        default_factory=list, description="유사 자격증 비교 (SimilarCertificate 구조)"
    )

    # 도메인 분류
    domain: Optional[str] = Field(
        None, description="분야 분류 (예: IT/소프트웨어, 건설/건축)"
    )

    # 합격률
    passing_rate: Optional[float] = Field(None, description="합격률 (%)")

    # 조회수
    view_count: int = Field(default=0, description="조회수")

    # Timestamps
    created_at: datetime
    updated_at: datetime


class CertificateList(BaseModel):
    """Schema for paginated certificate list response."""

    items: list[Certificate]
    total: int
    page: int = 1
    page_size: int = 20
    has_more: bool = False


class CertificateSearchParams(BaseModel):
    """Schema for certificate search query parameters."""

    q: Optional[str] = Field(None, description="검색 키워드")
    categories: Optional[list[str]] = Field(
        None, description="자격구분명 필터 (여러 개 가능)"
    )
    category_codes: Optional[list[str]] = Field(
        None, description="자격구분코드 필터 (여러 개 가능)"
    )
    difficulty_min: Optional[int] = Field(None, ge=1, le=5, description="최소 난이도")
    difficulty_max: Optional[int] = Field(None, ge=1, le=5, description="최대 난이도")
    page: int = Field(1, ge=1, description="페이지 번호")
    page_size: int = Field(20, ge=1, le=100, description="페이지 크기")
