"""Pydantic schemas for Recommendation API.

This module defines request/response schemas for certificate recommendation endpoints.
"""

from pydantic import BaseModel, Field, field_validator

from app.core.constants import RecommendationConstants

from .certificate import Certificate

# Valid values for each field
VALID_PURPOSES = [
    "취업",
    "이직",
    "커리어 전문성 강화",
    "개인 관심 / 교양",
    "창업 / 실무 활용",
]

VALID_INTEREST_DOMAINS = [
    "기획/전략",
    "마케팅/홍보/조사",
    "회계/세무/재무",
    "인사/노무/HRD",
    "총무/법무/사무",
    "IT개발",
    "데이터",
    "디자인",
    "영업/판매/무역",
    "고객상담/TM",
    "구매/자재/물류",
    "상품기획/MD",
    "운전/운송/배송",
    "서비스",
    "생산",
    "건설/건축",
    "의료",
    "연구/R&D",
    "교육",
    "미디어/문화/스포츠",
    "금융/보험",
    "공공/복지",
]

VALID_TIMELINES = [
    "3개월 이하",
    "6개월 이하",
    "1년 이하",
    "1년 이상",
    "상관없음",
]

VALID_DIFFICULTY_PREFERENCES = [
    "쉬운 편",
    "중간",
    "어려워도 상관없음",
]

# 새 필드: 현재 상황
VALID_CURRENT_STATUS = [
    "student",  # 학생 (취업 준비 중인 대학생/취준생)
    "entry_jobseeker",  # 신입 구직자 (첫 직장을 찾고 있어요)
    "junior_worker",  # 현직자 1-3년차 (경력 개발 또는 이직 준비)
    "senior_worker",  # 현직자 4년차 이상 (전문성 강화 또는 커리어 전환)
    "career_break",  # 휴직/전업준비 (재취업 또는 새로운 시작)
]

# 새 필드: 투자 시간
VALID_STUDY_COMMITMENT = [
    "relaxed",  # 여유 있게 (일상과 병행하며 천천히)
    "moderate",  # 적당히 (주 10시간 정도 투자 가능)
    "intensive",  # 집중해서 (전업으로 빠르게 취득 목표)
    "unsure",  # 잘 모르겠어요 (추천받고 결정할게요)
]

# 새 필드: 자격증 등급 선호
VALID_CERTIFICATE_LEVELS = [
    "기능장",  # 기능장 등급 (최고급)
    "기사",  # 기사 등급
    "산업기사",  # 산업기사 등급
    "기능사",  # 기능사 등급 (입문)
    "상관없음",  # 등급 상관없음
]


# Contextual Retrieval 구조화된 추천 요청
VALID_STRUCTURED_PURPOSES = [
    "취업",
    "이직",
    "전문성 강화",
    "실무 활용",
    "교양",
]

VALID_STRUCTURED_STATUS = [
    "학생",
    "취준생",
    "직장인",
    "경력자",
    "전업 준비",
]

VALID_PREFERENCE_TAGS = [
    "독학 가능",
    "비전공자",
    "비용 저렴",
    "CBT 상시시험",
]


class StructuredRecommendationRequest(BaseModel):
    """구조화된 추천 요청 (Contextual Retrieval)."""

    domains: list[str] = Field(..., min_length=1, description="관심 분야")
    purpose: str = Field(..., description="목적")
    current_status: str = Field(..., description="현재 상황")
    preference_tags: list[str] = Field(default_factory=list, description="선호 태그")
    additional_input: str = Field(default="", max_length=1000, description="추가 입력")

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        if v not in VALID_STRUCTURED_PURPOSES:
            raise ValueError(
                f"Invalid purpose: {v}. Must be one of {VALID_STRUCTURED_PURPOSES}"
            )
        return v

    @field_validator("current_status")
    @classmethod
    def validate_current_status(cls, v: str) -> str:
        if v not in VALID_STRUCTURED_STATUS:
            raise ValueError(
                f"Invalid status: {v}. Must be one of {VALID_STRUCTURED_STATUS}"
            )
        return v

    @field_validator("preference_tags")
    @classmethod
    def validate_preference_tags(cls, v: list[str]) -> list[str]:
        for tag in v:
            if tag not in VALID_PREFERENCE_TAGS:
                raise ValueError(
                    f"Invalid tag: {tag}. Must be one of {VALID_PREFERENCE_TAGS}"
                )
        return v


class RecommendationRequest(BaseModel):
    """사용자 컨텍스트 기반 추천 요청 스키마."""

    purpose: str = Field(
        ...,
        description="자격증 취득 목적/맥락 (취업, 이직, 전문성 강화, 교양, 창업/실무 활용)",
    )
    interest_domains: list[str] = Field(
        ...,
        min_length=1,
        description="관심 분야 (복수 선택 가능)",
    )
    study_timeline: str = Field(
        ...,
        description="예상 공부 기간 (3개월 이하, 6개월 이하, 1년 이하, 1년 이상, 상관없음)",
    )
    difficulty_preference: str = Field(
        ...,
        description="난이도 선호 (쉬운 편, 중간, 어려워도 상관없음)",
    )
    user_summary: str | None = Field(
        default=None,
        description="사용자가 작성한 한 문장 요약 (선택, 없으면 자동 생성)",
    )
    current_status: str | None = Field(
        default=None,
        description="현재 상황 (student, entry_jobseeker, junior_worker, senior_worker, career_break)",
    )
    study_commitment: str | None = Field(
        default=None,
        description="투자 시간 (relaxed, moderate, intensive, unsure)",
    )
    target_jobs: list[str] | None = Field(
        default=None,
        description="목표 직종 키워드 (예: ['전기기술자', '전기안전관리자'])",
    )
    target_industries: list[str] | None = Field(
        default=None,
        description="산업 분야 키워드 (예: ['전기공사', '제조업'])",
    )
    certificate_level: str | None = Field(
        default=None,
        description="자격증 등급 선호 (기능장, 기사, 산업기사, 기능사, 상관없음)",
    )
    specific_keywords: list[str] | None = Field(
        default=None,
        description="특정 키워드 (예: ['전기', '정보처리'])",
    )

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        if v not in VALID_PURPOSES:
            raise ValueError("Invalid purpose. " f"Must be one of: {VALID_PURPOSES}")
        return v

    @field_validator("interest_domains")
    @classmethod
    def validate_interest_domains(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("interest_domains must contain at least one domain")

        invalid = [domain for domain in v if domain not in VALID_INTEREST_DOMAINS]
        if invalid:
            raise ValueError(
                f"Invalid interest_domains: {invalid}. "
                f"Allowed values: {VALID_INTEREST_DOMAINS}"
            )

        # Remove duplicates while preserving order
        seen = set()
        deduped = []
        for domain in v:
            if domain not in seen:
                deduped.append(domain)
                seen.add(domain)
        return deduped

    @field_validator("study_timeline")
    @classmethod
    def validate_timeline(cls, v: str) -> str:
        if v not in VALID_TIMELINES:
            raise ValueError(
                f"Invalid study_timeline. Must be one of: {VALID_TIMELINES}"
            )
        return v

    @field_validator("difficulty_preference")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        if v not in VALID_DIFFICULTY_PREFERENCES:
            raise ValueError(
                f"Invalid difficulty_preference. Must be one of: {VALID_DIFFICULTY_PREFERENCES}"
            )
        return v

    @field_validator("user_summary")
    @classmethod
    def validate_user_summary(cls, v: str) -> str:
        if v is None:
            return None
        text = v.strip()
        return text or None

    @field_validator("current_status")
    @classmethod
    def validate_current_status(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v not in VALID_CURRENT_STATUS:
            raise ValueError(
                f"Invalid current_status. Must be one of: {VALID_CURRENT_STATUS}"
            )
        return v

    @field_validator("study_commitment")
    @classmethod
    def validate_study_commitment(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v not in VALID_STUDY_COMMITMENT:
            raise ValueError(
                f"Invalid study_commitment. Must be one of: {VALID_STUDY_COMMITMENT}"
            )
        return v

    @field_validator("target_jobs")
    @classmethod
    def validate_target_jobs(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        # 공백만 있는 항목 제거
        filtered = [item.strip() for item in v if item and item.strip()]
        return filtered if filtered else None

    @field_validator("target_industries")
    @classmethod
    def validate_target_industries(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        # 공백만 있는 항목 제거
        filtered = [item.strip() for item in v if item and item.strip()]
        return filtered if filtered else None

    @field_validator("certificate_level")
    @classmethod
    def validate_certificate_level(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if v not in VALID_CERTIFICATE_LEVELS:
            raise ValueError(
                f"Invalid certificate_level. Must be one of: {VALID_CERTIFICATE_LEVELS}"
            )
        return v

    @field_validator("specific_keywords")
    @classmethod
    def validate_specific_keywords(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        # 공백만 있는 항목 제거 및 중복 제거
        seen = set()
        deduped = []
        for item in v:
            if item and item.strip():
                cleaned = item.strip()
                if cleaned not in seen:
                    deduped.append(cleaned)
                    seen.add(cleaned)
        return deduped if deduped else None


class Feasibility(BaseModel):
    """추천 자격증의 준비 가능성 정보."""

    can_prepare: bool = Field(
        ...,
        description="목표 기간 내 준비 가능 여부",
    )
    estimated_days: int = Field(
        ...,
        ge=1,
        description="예상 준비 기간 (일)",
    )


class QuickStats(BaseModel):
    """핵심 통계 정보."""

    passing_rate: float | None = Field(
        default=None,
        description="합격률 (%)",
    )
    average_salary: str | None = Field(
        default=None,
        description="평균 연봉",
    )
    exam_fee: str | None = Field(
        default=None,
        description="응시료",
    )
    exam_type: str | None = Field(
        default=None,
        description="시험 유형 (필기/실기 등)",
    )


class StudyInsights(BaseModel):
    """학습 인사이트."""

    study_tips: list[str] = Field(
        default_factory=list,
        description="학습 팁 (최대 3개)",
    )
    success_tips: list[str] = Field(
        default_factory=list,
        description="합격 팁 (최대 2개)",
    )
    difficulty_feedback: str | None = Field(
        default=None,
        description="실제 난이도 피드백",
    )


class RecommendedCertificate(BaseModel):
    """추천된 자격증 정보."""

    certificate: Certificate = Field(
        ...,
        description="자격증 상세 정보",
    )
    qualification_category: str = Field(
        ...,
        description="자격 구분명 (국가전문자격, 국가기술자격 등)",
    )
    match_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="사용자 컨텍스트와의 매칭 점수 (0-100)",
    )
    recommendation_reason: str = Field(
        ...,
        description="추천 이유 (2-3문장)",
    )
    key_points: list[str] = Field(
        default_factory=list,
        description="핵심 추천 포인트 (최대 5개)",
    )
    feasibility: Feasibility = Field(
        ...,
        description="준비 가능성 정보",
    )
    quick_stats: QuickStats = Field(
        default_factory=QuickStats,
        description="핵심 통계 정보 (합격률, 연봉, 응시료 등)",
    )
    study_insights: StudyInsights = Field(
        default_factory=StudyInsights,
        description="학습 인사이트 (학습 팁, 합격 팁 등)",
    )


class RecommendationResponse(BaseModel):
    """추천 결과 응답 스키마."""

    recommendations: list[RecommendedCertificate] = Field(
        default_factory=list,
        description="추천 자격증 목록 (최대 10개)",
    )
    query_summary: str = Field(
        ...,
        description="사용자 요청 요약 (예: 'IT 분야 취업 준비를 위한 자격증 추천')",
    )
    user_summary: str | None = Field(
        default=None,
        description="사용자가 입력한 원본 요청 문장 (선택)",
    )
    total_matched: int = Field(
        ...,
        ge=0,
        description="조건에 맞는 전체 자격증 수",
    )


# ===== 자연어 기반 추천 스키마 (NEW) =====

# 자연어 추천에서 사용하는 유효 값들 (constants에서 중앙 관리)
VALID_NATURAL_GOALS = RecommendationConstants.NATURAL_GOALS
VALID_EMPLOYMENT_STATUS = RecommendationConstants.EMPLOYMENT_STATUS
VALID_MAJOR_BACKGROUND = RecommendationConstants.MAJOR_BACKGROUND
VALID_NATURAL_DIFFICULTY = RecommendationConstants.NATURAL_DIFFICULTY


class StructuredUserContext(BaseModel):
    """LLM이 구조화한 사용자 상황 (사용자 선호).

    자연어 입력을 LLM이 분석하여 생성하는 구조화된 컨텍스트입니다.

    Attributes:
        preferred_industries: 사용자가 취업하고 싶은 산업 분야.
            예: ["IT", "스타트업", "게임"] (사용자의 희망 산업)
            ※ 다른 industry 필드들과 다름:
            - career_info.industry: 자격증이 '관련된' 산업 (자격증 속성)
            - job_market_info.preferred_industries: 자격증을 '선호하는' 기업군 (채용 관점)
            - 이 필드: 사용자가 '가고 싶은' 산업 (개인 선호)
    """

    goal: str = Field(
        ...,
        description="자격증 취득 목표 (취업, 이직, 전문성 강화, 개인 관심, 창업)",
    )
    employment_status: str = Field(
        ...,
        description="현재 고용 상태 (재직 중, 구직 중, 학생, 무직)",
    )
    major_background: str = Field(
        ...,
        description="전공/경력 배경 (전공자, 비전공자, 관련 경험 있음)",
    )
    weekly_study_hours: int = Field(
        ...,
        ge=1,
        le=40,
        description="주당 학습 가능 시간 (1-40시간)",
    )
    max_study_period_days: int = Field(
        ...,
        ge=30,
        le=730,
        description="최대 준비 기간 (30-730일, 약 1개월~2년)",
    )
    difficulty_preference: str = Field(
        ...,
        description="난이도 선호 (상, 중상, 중, 중하, 하)",
    )
    preferred_industries: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="사용자가 취업하고 싶은 산업 (예: IT, 금융, 게임) - 최대 5개",
    )

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        if v not in VALID_NATURAL_GOALS:
            raise ValueError(f"Invalid goal. Must be one of: {VALID_NATURAL_GOALS}")
        return v

    @field_validator("employment_status")
    @classmethod
    def validate_employment_status(cls, v: str) -> str:
        if v not in VALID_EMPLOYMENT_STATUS:
            raise ValueError(
                f"Invalid employment_status. Must be one of: {VALID_EMPLOYMENT_STATUS}"
            )
        return v

    @field_validator("major_background")
    @classmethod
    def validate_major_background(cls, v: str) -> str:
        if v not in VALID_MAJOR_BACKGROUND:
            raise ValueError(
                f"Invalid major_background. Must be one of: {VALID_MAJOR_BACKGROUND}"
            )
        return v

    @field_validator("difficulty_preference")
    @classmethod
    def validate_difficulty_preference(cls, v: str) -> str:
        if v not in VALID_NATURAL_DIFFICULTY:
            raise ValueError(
                f"Invalid difficulty_preference. Must be one of: {VALID_NATURAL_DIFFICULTY}"
            )
        return v

    @field_validator("preferred_industries")
    @classmethod
    def validate_preferred_industries(cls, v: list[str]) -> list[str]:
        if len(v) > 5:
            raise ValueError("preferred_industries must contain at most 5 items")
        return v


class NaturalLanguageRequest(BaseModel):
    """자연어 기반 추천 요청.

    사용자의 자유로운 자연어 입력을 받습니다.
    """

    user_input: str = Field(
        ...,
        min_length=10,
        max_length=1000,
        description="사용자 자연어 입력 (10-1000자)",
    )


class NaturalLanguageResponse(BaseModel):
    """자연어 추천 응답.

    LLM이 구조화한 컨텍스트와 추천 결과를 포함합니다.
    """

    structured_context: StructuredUserContext = Field(
        ...,
        description="LLM이 구조화한 사용자 상황",
    )
    recommendations: list[RecommendedCertificate] = Field(
        default_factory=list,
        description="추천 자격증 목록",
    )
    query_used: str = Field(
        ...,
        description="벡터 검색에 사용된 쿼리",
    )
    follow_up_question: str | None = Field(
        default=None,
        description="추가 질문 (정보 부족 시)",
    )
    total_matched: int = Field(
        ...,
        ge=0,
        description="조건에 맞는 전체 자격증 수",
    )


# ===== 변환 함수 =====


def structured_to_recommendation_request(
    context: StructuredUserContext,
) -> RecommendationRequest:
    """자연어 추천의 StructuredUserContext를 기존 RecommendationRequest로 변환합니다.

    이 함수는 자연어 추천 시스템과 기존 추천 시스템 간의 호환성을 제공합니다.

    Args:
        context: 자연어 입력에서 추출된 구조화된 사용자 컨텍스트

    Returns:
        RecommendationRequest: 기존 추천 API에서 사용 가능한 요청 객체
    """
    # goal → purpose 매핑
    goal_to_purpose = {
        "취업": "취업",
        "이직": "이직",
        "전문성 강화": "커리어 전문성 강화",
        "개인 관심": "개인 관심 / 교양",
        "창업": "창업 / 실무 활용",
    }
    purpose = goal_to_purpose.get(context.goal, "취업")

    # max_study_period_days → study_timeline 매핑
    days = context.max_study_period_days
    if days <= 90:
        study_timeline = "3개월 이하"
    elif days <= 180:
        study_timeline = "6개월 이하"
    elif days <= 365:
        study_timeline = "1년 이하"
    else:
        study_timeline = "1년 이상"

    # difficulty_preference 매핑 (5단계 → 3단계)
    difficulty_map = {
        "하": "쉬운 편",
        "중하": "쉬운 편",
        "중": "중간",
        "중상": "어려워도 상관없음",
        "상": "어려워도 상관없음",
    }
    difficulty = difficulty_map.get(context.difficulty_preference, "중간")

    # employment_status → current_status 매핑
    status_map = {
        "학생": "student",
        "구직 중": "entry_jobseeker",
        "재직 중": "junior_worker",  # 기본값, 연차 정보 없음
        "무직": "career_break",
    }
    current_status = status_map.get(context.employment_status)

    # weekly_study_hours → study_commitment 매핑
    hours = context.weekly_study_hours
    if hours <= 10:
        study_commitment = "relaxed"
    elif hours <= 20:
        study_commitment = "moderate"
    else:
        study_commitment = "intensive"

    # preferred_industries 처리
    # 자연어 추천의 preferred_industries는 자유 형식이라
    # interest_domains (고정 목록)로 변환하기 어려움
    # → target_industries로 전달
    target_industries = (
        context.preferred_industries if context.preferred_industries else None
    )

    # interest_domains는 기본값 사용 (자연어에서 정확히 매핑 불가)
    # 사용자의 preferred_industries 기반으로 가장 관련있는 도메인 추론
    interest_domains = _infer_interest_domains(context.preferred_industries)

    return RecommendationRequest(
        purpose=purpose,
        interest_domains=interest_domains,
        study_timeline=study_timeline,
        difficulty_preference=difficulty,
        current_status=current_status,
        study_commitment=study_commitment,
        target_industries=target_industries,
    )


def _infer_interest_domains(preferred_industries: list[str]) -> list[str]:
    """preferred_industries에서 interest_domains를 추론합니다.

    자연어로 입력된 산업 키워드를 VALID_INTEREST_DOMAINS에 매핑합니다.
    """
    if not preferred_industries:
        return ["IT개발"]  # 기본값

    # 키워드 → 도메인 매핑
    keyword_to_domain = {
        "IT": "IT개발",
        "개발": "IT개발",
        "소프트웨어": "IT개발",
        "데이터": "데이터",
        "AI": "데이터",
        "금융": "금융/보험",
        "은행": "금융/보험",
        "증권": "금융/보험",
        "보험": "금융/보험",
        "회계": "회계/세무/재무",
        "세무": "회계/세무/재무",
        "재무": "회계/세무/재무",
        "마케팅": "마케팅/홍보/조사",
        "홍보": "마케팅/홍보/조사",
        "디자인": "디자인",
        "건설": "건설/건축",
        "건축": "건설/건축",
        "의료": "의료",
        "교육": "교육",
        "공공": "공공/복지",
        "공기업": "공공/복지",
        "게임": "IT개발",
        "스타트업": "IT개발",
    }

    domains = set()
    for industry in preferred_industries:
        for keyword, domain in keyword_to_domain.items():
            if keyword in industry:
                domains.add(domain)
                break
        else:
            # 매핑 안되면 기본값
            domains.add("IT개발")

    return list(domains)[:3]  # 최대 3개


# ===== 통합 추천 스키마 (Redesign) =====


class UnifiedRecommendationRequest(BaseModel):
    """통합 추천 요청 (분야 선택 + 자연어).

    기존 RecommendationRequest(위저드)와 NaturalLanguageRequest를 통합합니다.
    """

    domains: list[str] = Field(
        default=[],
        description="선택한 분야 목록 (빈 리스트 시 자동 추론)",
    )
    user_input: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="자연어 입력 (5-1000자)",
    )

    @field_validator("domains")
    @classmethod
    def validate_domains(cls, v: list[str]) -> list[str]:
        if not v:
            return v  # 빈 리스트 허용 (자동 추론)
        from app.core.domains import DOMAIN_LIST

        invalid = [d for d in v if d not in DOMAIN_LIST]
        if invalid:
            raise ValueError(f"Invalid domains: {invalid}")
        return v


class SearchStats(BaseModel):
    """하이브리드 검색 통계."""

    dense_count: int = Field(..., description="Dense 검색 결과 수")
    sparse_count: int = Field(..., description="Sparse(BM25) 검색 결과 수")
    merged_count: int = Field(..., description="RRF 결합 후 최종 결과 수")
    elapsed_ms: float = Field(..., description="총 검색 소요 시간 (ms)")


class UnifiedRecommendationResponse(BaseModel):
    """통합 추천 응답."""

    structured_context: StructuredUserContext = Field(
        ...,
        description="LLM이 구조화한 사용자 상황",
    )
    recommendations: list[RecommendedCertificate] = Field(
        default_factory=list,
        description="추천 자격증 목록",
    )
    query_used: str = Field(
        ...,
        description="벡터 검색에 사용된 쿼리",
    )
    total_matched: int = Field(
        ...,
        ge=0,
        description="조건에 맞는 전체 자격증 수",
    )
    search_stats: SearchStats | None = Field(
        default=None,
        description="하이브리드 검색 통계",
    )
