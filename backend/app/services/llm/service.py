"""2단계 처리로 자격증 정보 보강을 수행하는 LLM 서비스.

1단계: 검색 결과에서 구조화 데이터 추출
2단계: 추출 데이터 정제 및 보강
"""

import json
import re
import time
from typing import Optional

from openai import AsyncOpenAI, BadRequestError
from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.config import get_settings

# JSON 복구 설정
MAX_RETRIES = 2  # 최대 재시도 횟수

# 난이도별 허용 study_period_days 범위 (프롬프트 난이도 기준과 동기화)
DIFFICULTY_PERIOD_RANGES: dict[int, tuple[int, int]] = {
    1: (1, 21),  # 1~3주: 누구나 쉽게 합격 가능
    2: (14, 90),  # 2주~3개월: 기초 지식으로 합격 가능
    3: (60, 210),  # 2~7개월: 체계적 학습 필요
    4: (150, 540),  # 5개월~1.5년: 전문 지식 및 집중 학습 필요
    5: (300, 1095),  # 10개월~3년: 매우 높은 난이도, 장기 준비 필수
}


def clamp_study_period(difficulty: int, study_period_days: int) -> int:
    """difficulty 기준으로 study_period_days를 허용 범위 내로 클램핑합니다."""
    min_days, max_days = DIFFICULTY_PERIOD_RANGES.get(difficulty, (1, 1095))
    return max(min_days, min(study_period_days, max_days))


# LLM이 정보 없을 때 생성하는 placeholder 교재 제목들
PLACEHOLDER_BOOK_TITLES: set[str] = {
    "교재명",
    "책 제목",
    "도서명",
    "추천 교재",
    "교재",
    "기본서",
    "책",
    "수험서",
    "문제집",
    "기출문제집",
    "요약집",
}


# Phase 1: Extraction Models
class ExtractedExamInfo(BaseModel):
    """검색 결과에서 추출한 시험 정보."""

    subjects: list[str] = Field(default_factory=list)
    exam_type: str = Field(default="")
    passing_criteria: str = Field(default="")
    total_fee: Optional[str] = None  # Changed to str to handle "20,000원", "무료" etc.
    acquisition_method: Optional[str] = None  # 취득 방법 (응시자격, 취득 절차)
    exam_criteria_url: Optional[str] = None  # 출제 기준 링크

    @field_validator("exam_type", "passing_criteria", mode="before")
    @classmethod
    def coerce_none_to_empty_string(cls, v):
        """None 값을 빈 문자열로 변환합니다."""
        if v is None:
            return ""
        return v

    @field_validator("total_fee", mode="before")
    @classmethod
    def coerce_total_fee_to_str(cls, v):
        """숫자 응시료를 문자열로 변환해 검증을 허용합니다."""
        if v is None or isinstance(v, str):
            return v
        return str(v)


# ExamSchedule and Eligibility removed - users should check official sources for these


class ExtractedCareerInfo(BaseModel):
    """추출된 진로 정보 (자격증 속성).

    이 모델은 자격증 자체의 속성으로서 진로 정보를 담습니다.

    Attributes:
        industry: 이 자격증이 활용되는 산업 분야.
            예: ["IT", "금융", "제조"] (일반적 산업 분류)
            ※ job_market_info.preferred_industries와 다름:
            - industry: 자격증이 '관련된' 산업 (자격증 속성)
            - preferred_industries: 자격증을 '선호하는' 기업군 (채용 관점)
    """

    use_cases: list[str] = Field(default_factory=list)
    related_jobs: list[str] = Field(default_factory=list)
    average_salary: Optional[str] = None
    job_prospects: Optional[str] = None
    industry: list[str] = Field(
        default_factory=list,
        description="자격증이 활용되는 산업 분야 (예: IT, 금융, 제조)",
    )


class ExtractedUserReviews(BaseModel):
    """추출된 사용자 후기."""

    summary: Optional[str] = None
    difficulty_feedback: Optional[str] = None
    difficulty_breakdown: Optional[dict] = None
    study_tips: list[str] = Field(default_factory=list)
    common_challenges: list[str] = Field(default_factory=list)


class ExtractedOfficialSources(BaseModel):
    """추출된 공식 출처."""

    official_site: Optional[str] = None
    issuing_organization: Optional[str] = None
    reference_urls: list[str] = Field(default_factory=list)


class ExtractedLecture(BaseModel):
    """추출된 강의 정보."""

    platform: str
    title: str
    url: str
    instructor: Optional[str] = None
    price: Optional[str] = None  # Changed to str to handle "50만원", "무료" etc.


class ExtractedKeyExamTopic(BaseModel):
    """추출된 핵심 출제 토픽."""

    topic: str
    frequency: str  # '매우 자주', '자주', '보통', '가끔'
    importance: str  # '상', '중', '하'
    description: Optional[str] = None


class ExtractedStudyGuide(BaseModel):
    """추출된 학습 가이드 정보."""

    study_methods: list[str] = Field(default_factory=list)
    key_exam_topics: list[dict] = Field(default_factory=list)
    time_allocation: Optional[dict] = None
    recommended_books: list[dict] = Field(default_factory=list)
    success_tips: list[str] = Field(default_factory=list)

    @field_validator("recommended_books", mode="before")
    @classmethod
    def sanitize_books(cls, v: list[dict] | None) -> list[dict]:
        """추천 교재를 자동으로 정제합니다.

        - None → 빈 리스트
        - placeholder 제목 필터링
        - 빈 title/publisher 필터링
        - 중복 제거
        """
        if v is None or not isinstance(v, list):
            return []

        sanitized = []
        seen_keys = set()

        for book in v:
            if not isinstance(book, dict):
                continue

            title = str(book.get("title") or "").strip()
            publisher = str(book.get("publisher") or "").strip()

            # 필수 필드 검증
            if not title or not publisher:
                continue

            # placeholder 제목 제외 (모듈 레벨 상수 참조)
            if title in PLACEHOLDER_BOOK_TITLES:
                continue

            # 중복 제거 (대소문자 무시)
            key = (title.casefold(), publisher.casefold())
            if key in seen_keys:
                continue

            seen_keys.add(key)

            # 정제된 교재 추가
            description = str(book.get("description") or "").strip()
            book_type = str(book.get("type") or "").strip()

            sanitized.append(
                {
                    "title": title,
                    "publisher": publisher,
                    "type": book_type or None,
                    "description": description or None,
                }
            )

        return sanitized


# ============================================================
# 취업준비생 관점 추출 모델 (NEW: 2026-01-28)
# ============================================================


class ExtractedJobMarketInfo(BaseModel):
    """추출된 채용 시장 정보 (시장 관점).

    이 모델은 채용 시장 관점에서 자격증의 가치를 담습니다.

    Attributes:
        preferred_industries: 이 자격증을 선호/우대하는 기업군.
            예: ["세무법인", "회계법인", "대기업 재무팀"] (구체적 기업 유형)
            ※ career_info.industry와 다름:
            - industry: 자격증이 '관련된' 산업 (자격증 속성)
            - preferred_industries: 자격증을 '선호하는' 기업군 (채용 관점)
    """

    job_posting_frequency: Optional[str] = None
    preferred_industries: list[str] = Field(
        default_factory=list,
        description="이 자격증을 선호하는 기업군 (예: 세무법인, 대기업 재무팀)",
    )
    requirement_type: Optional[str] = None
    public_sector_points: Optional[str] = None

    @field_validator("preferred_industries", mode="before")
    @classmethod
    def coerce_none_to_empty_list(cls, v):
        """None 값을 빈 리스트로 변환합니다."""
        if v is None:
            return []
        return v


class ExtractedCostBreakdown(BaseModel):
    """추출된 비용 상세 정보."""

    exam_fee: Optional[str] = None
    exam_fee_refund: Optional[str] = None
    textbook_cost: Optional[str] = None
    lecture_cost: Optional[str] = None
    free_resources: list[str] = Field(default_factory=list)


class ExtractedFeasibilityInfo(BaseModel):
    """추출된 합격 가능성 정보."""

    non_major_pass_rate: Optional[str] = None
    self_study_possible: Optional[bool] = None
    minimum_study_period: Optional[int] = None
    first_attempt_pass_rate: Optional[str] = None


class ExtractedExamScheduleDetail(BaseModel):
    """추출된 시험 일정 상세 정보."""

    annual_exam_count: Optional[int] = None
    exam_type: Optional[str] = None
    next_exam_date: Optional[str] = None
    registration_period: Optional[str] = None
    result_announcement: Optional[str] = None


class ExtractedSimilarCertificate(BaseModel):
    """추출된 유사 자격증 정보."""

    certificate_id: Optional[str] = None
    title: str
    comparison: Optional[str] = None


class Phase1Extraction(BaseModel):
    """1단계: 검색 결과에서 원시 데이터를 추출합니다."""

    overview_draft: str = Field(..., description="초안 개요 (1-2문장)")
    difficulty: int = Field(..., ge=1, le=5)
    study_period_days: int = Field(..., ge=1, le=1095)

    @field_validator("difficulty", mode="before")
    @classmethod
    def coerce_difficulty_to_int(cls, v):
        """None 또는 유효하지 않은 difficulty를 기본값 3으로 변환합니다."""
        if v is None:
            return 3  # 기본값: 보통 난이도
        if isinstance(v, (int, float)):
            return int(v)
        return v

    @field_validator("study_period_days", mode="before")
    @classmethod
    def coerce_study_period_to_int(cls, v):
        """None 또는 유효하지 않은 study_period_days를 기본값 90으로 변환합니다."""
        if v is None:
            return 90  # 기본값: 3개월
        if isinstance(v, (int, float)):
            clamped = max(1, min(int(v), 1095))
            return clamped
        return v

    @model_validator(mode="after")
    def validate_difficulty_period_consistency(self):
        """difficulty와 study_period_days 간 정합성을 검증하고 보정합니다."""
        self.study_period_days = clamp_study_period(
            self.difficulty, self.study_period_days
        )
        return self

    exam_info: ExtractedExamInfo
    career_info: ExtractedCareerInfo
    user_reviews: ExtractedUserReviews
    study_guide: ExtractedStudyGuide
    official_sources: ExtractedOfficialSources
    lectures: list[ExtractedLecture] = Field(default_factory=list)
    # 취업준비생 관점 필드 (NEW: 2026-01-28)
    job_market_info: ExtractedJobMarketInfo = Field(
        default_factory=ExtractedJobMarketInfo
    )
    cost_breakdown: ExtractedCostBreakdown = Field(
        default_factory=ExtractedCostBreakdown
    )
    feasibility_info: ExtractedFeasibilityInfo = Field(
        default_factory=ExtractedFeasibilityInfo
    )
    exam_schedule_detail: ExtractedExamScheduleDetail = Field(
        default_factory=ExtractedExamScheduleDetail
    )
    similar_certificates: list[ExtractedSimilarCertificate] = Field(
        default_factory=list
    )


# Phase 2: Refined Models
class RefinedLecture(BaseModel):
    """관련성 점수를 포함한 정제 강의 정보."""

    platform: str
    title: str
    url: str
    instructor: Optional[str] = None
    price: Optional[str] = None  # Changed to str to handle various formats
    relevance_score: float = Field(..., ge=0, le=1)


class CertificateEnrichment(BaseModel):
    """최종 보강된 자격증 데이터."""

    overview: str = Field(..., description="정제된 개요 (3-5문장)")
    difficulty: int = Field(..., ge=1, le=5)
    study_period_days: int = Field(..., ge=1, le=1095)
    exam_info: dict
    career_info: dict
    user_reviews: dict
    study_guide: dict
    official_sources: dict
    recommended_lectures: list[dict] = Field(
        default_factory=list
    )  # Optional: 덜 유명한 자격증은 추천 강의 없을 수 있음
    # 취업준비생 관점 필드 (NEW: 2026-01-28)
    job_market_info: dict = Field(default_factory=dict)
    cost_breakdown: dict = Field(default_factory=dict)
    feasibility_info: dict = Field(default_factory=dict)
    exam_schedule_detail: dict = Field(default_factory=dict)
    similar_certificates: list[dict] = Field(default_factory=list)

    @field_validator("study_period_days", mode="before")
    @classmethod
    def coerce_enrichment_study_period(cls, v):
        """study_period_days를 정수로 변환하고 상한을 적용합니다."""
        if v is None:
            return 90
        if isinstance(v, (int, float)):
            return max(1, min(int(v), 1095))
        return v

    @model_validator(mode="after")
    def validate_difficulty_period_consistency(self):
        """difficulty와 study_period_days 간 정합성을 검증하고 보정합니다."""
        self.study_period_days = clamp_study_period(
            self.difficulty, self.study_period_days
        )
        return self


class LLMService:
    """2단계 처리로 LLM 기반 자격증 보강을 수행하는 서비스.

    OpenAI API (GPT-4o-mini)를 사용합니다.
    """

    # temperature를 지원하지 않는 모델 목록
    MODELS_WITHOUT_TEMPERATURE = {"gpt-5-nano"}

    def __init__(self, api_key: Optional[str] = None):
        """LLM 서비스를 초기화합니다.

        Args:
            api_key: API 키. 제공되지 않으면 설정 값을 사용합니다.
        """
        settings = get_settings()

        self.provider_name = "openai"
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL_NAME

        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key)
        else:
            self.client = None

    def should_skip_temperature(self) -> bool:
        """현재 모델이 temperature 파라미터를 지원하지 않는지 확인합니다.

        Returns:
            True: temperature를 건너뛰어야 함 (지원하지 않는 모델)
            False: temperature를 사용해야 함 (지원하는 모델)
        """
        return self.model in self.MODELS_WITHOUT_TEMPERATURE

    def build_completion_params(
        self,
        messages: list[dict],
        temperature: Optional[float] = None,
        response_format: Optional[dict] = None,
    ) -> dict:
        """LLM API 호출을 위한 파라미터를 생성합니다.

        temperature를 지원하지 않는 모델의 경우 해당 파라미터를 제외합니다.

        Args:
            messages: 메시지 목록.
            temperature: 응답의 창의성 정도 (0.0 ~ 2.0).
            response_format: 응답 형식 지정.

        Returns:
            API 호출용 파라미터 딕셔너리.
        """
        params = {
            "model": self.model,
            "messages": messages,
        }

        # temperature를 지원하는 모델일 때만 추가
        if temperature is not None and not self.should_skip_temperature():
            params["temperature"] = temperature

        if response_format is not None:
            params["response_format"] = response_format

        return params

    @staticmethod
    def _try_repair_json(failed_json: str) -> Optional[dict]:
        """잘못된 JSON을 복구 시도합니다.

        Args:
            failed_json: 잘못된 JSON 문자열.

        Returns:
            복구된 딕셔너리 또는 None.
        """
        if not failed_json:
            return None

        try:
            # 1. 먼저 그대로 파싱 시도
            return json.loads(failed_json)
        except json.JSONDecodeError:
            pass

        try:
            # 2. 문자열 내 이스케이프되지 않은 줄바꿈을 \\n으로 변환
            # JSON 문자열 값 내의 실제 줄바꿈을 찾아 이스케이프
            repaired = failed_json

            # 문자열 값 내의 줄바꿈을 \\n으로 변환
            # "key": "value with
            # newline" -> "key": "value with\\nnewline"
            def fix_newlines_in_strings(match):
                content = match.group(1)
                # 실제 줄바꿈을 \\n으로 변환
                fixed = content.replace("\n", "\\n").replace("\r", "\\r")
                return f'"{fixed}"'

            # 따옴표로 둘러싸인 문자열 내용 처리
            repaired = re.sub(
                r'"([^"\\]*(?:\\.[^"\\]*)*)"',
                fix_newlines_in_strings,
                repaired,
                flags=re.DOTALL,
            )

            return json.loads(repaired)
        except (json.JSONDecodeError, re.error):
            pass

        try:
            # 3. 마지막 중괄호/대괄호가 누락된 경우 추가
            open_braces = repaired.count("{") - repaired.count("}")
            open_brackets = repaired.count("[") - repaired.count("]")

            if open_braces > 0:
                repaired += "}" * open_braces
            if open_brackets > 0:
                repaired += "]" * open_brackets

            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

        return None

    @staticmethod
    def sanitize_recommended_books(books: list[dict]) -> list[dict]:
        """추천 교재를 필터링하고 중복을 제거합니다.

        자리표시 텍스트, 정보 부족 항목, 중복 항목을 제거합니다.

        Args:
            books: 교재 정보 딕셔너리 목록.

        Returns:
            정제된 교재 목록.
        """
        if not books or not isinstance(books, list):
            return []

        # 자리표시 텍스트 (LLM이 정보 없을 때 생성하는 placeholder)
        placeholder_titles = {
            "교재명",
            "책 제목",
            "도서명",
            "추천 교재",
            "교재",
            "기본서",
            "책",
            "수험서",
            "문제집",
            "기출문제집",
            "요약집",
        }

        sanitized = []
        seen_keys = set()

        for book in books:
            if not isinstance(book, dict):
                continue

            title = str(book.get("title") or "").strip()
            publisher = str(book.get("publisher") or "").strip()

            # 필수 필드 검증
            if not title or not publisher:
                continue

            # 자리표시 텍스트 제외
            if title in placeholder_titles:
                continue

            # 중복 제거
            key = (title.casefold(), publisher.casefold())
            if key in seen_keys:
                continue

            seen_keys.add(key)

            # 정제된 교재 추가
            description = str(book.get("description") or "").strip()
            book_type = str(book.get("type") or "").strip()

            sanitized.append(
                {
                    "title": title,
                    "publisher": publisher,
                    "type": book_type or None,
                    "description": description or None,
                }
            )

        return sanitized

    async def enrich_certificate(
        self, certificate_title: str, search_context: str
    ) -> CertificateEnrichment:
        """2단계 처리로 자격증 정보를 보강합니다.

        1단계: 검색 결과에서 구조화 데이터 추출
        2단계: 추출 데이터 정제 및 보강

        Args:
            certificate_title: 자격증명.
            search_context: 검색 결과를 포맷한 문자열.
        Returns:
            정제된 데이터가 담긴 CertificateEnrichment.
        """
        if not self.client:
            raise ValueError("OPENAI_API_KEY not configured")

        # 컨텍스트 길이 계산 (대략적인 토큰 수 추정)
        context_chars = len(search_context)
        context_tokens_est = context_chars // 2  # 한글 기준 대략 2자당 1토큰

        print(f"    [LLM] provider={self.provider_name}, model={self.model}")
        print(
            f"    [LLM] 입력 컨텍스트: {context_chars}자 (~{context_tokens_est} tokens)"
        )

        # Phase 1: Extract
        print(f"    [Phase 1] Extracting data... (model: {self.model})")
        start_time = time.time()
        extracted = await self._phase1_extract(certificate_title, search_context)
        phase1_time = time.time() - start_time
        print(f"    [Phase 1] 완료 ({phase1_time:.1f}초)")

        # Phase 2: Refine
        print(f"    [Phase 2] Refining data... (model: {self.model})")
        start_time = time.time()
        enriched = await self._phase2_refine(certificate_title, extracted)
        phase2_time = time.time() - start_time
        print(f"    [Phase 2] 완료 ({phase2_time:.1f}초)")

        return enriched

    async def _phase1_extract(
        self, certificate_title: str, search_context: str
    ) -> Phase1Extraction:
        """1단계: 검색 결과에서 구조화된 데이터를 추출합니다.

        Args:
            certificate_title: 자격증명.
            search_context: 검색 결과를 포맷한 문자열.
        """

        system_prompt = """당신은 한국 자격증 정보 추출 및 설명 전문가입니다.
검색 결과에서 정확한 정보만 추출하세요. 정보가 없으면 빈 값으로 두세요.
검색 결과 외의 텍스트나 사전 지식은 절대 사용하지 마세요.

자격증명: {certificate_title}

추출 규칙:
1. 검색 결과에 명시된 내용만 추출 (특히 url_quality 높은 것 우선)
2. 공식 사이트(.go.kr, q-net.or.kr) 정보 우선 사용
3. URL은 검색 결과의 실제 URL을 그대로 사용
4. 강의는 실제 강의 플랫폼(eduwill.net, hackers.com 등)만 선택
5. 커뮤니티/블로그 추천글은 강의 목록에서 제외

**[문체 규칙 - 필수]** ⭐중요:
- 모든 서술형 텍스트는 존댓말(~입니다, ~합니다, ~됩니다)로 작성하세요.
- "~이다", "~한다", "~좋다" 등 반말 종결어미는 절대 사용하지 마세요.
- 친절하고 정중한 어조로 작성하세요.
- 예시:
  - 좋음: "이 자격증은 IT 분야에서 필수적입니다."
  - 나쁨: "이 자격증은 IT 분야에서 필수이다." (반말 금지)

**준비 기간 추출 규칙** ⭐NEW:
- "2. 합격률 및 준비기간 통계" 및 "5. 합격 후기 및 팁" 카테고리 참고
- 실제 합격자들의 준비기간 수집 (1개월, 3개월, 6개월 등)
- 가장 많이 언급된 기간을 study_period_days로 설정
- 공식 권장 기간이 있으면 우선 사용

**난이도 추출 규칙** ⭐NEW:
- overall 난이도는 1-5 유지
- 필기/실기/면접 구분이 있으면 각각 난이도를 추정해 user_reviews.difficulty_breakdown에 포함
  예: {"overall": 3, "written": 2, "practical": 4, "interview": null}
- 난이도 근거를 user_reviews.difficulty_feedback에 2-3문장으로 서술

**시험 정보 추출 강화**:
- 시험 과목, 문항 수, 시험 시간, 시험 방식 (CBT/OMR)
- 과목별 배점, 합격 기준 (평균 60점 이상 등)
- 필기/실기 구분, 각 시험의 난이도 차이
- 최근 출제 경향, 자주 나오는 주제
- acquisition_method: 취득 방법 (응시자격, 취득 절차)
- exam_criteria_url: 출제 기준 링크 (공식 URL)

**학습 가이드 추출 강화**:
- 실제 합격자들의 구체적인 공부 방법
- 핵심 출제 토픽 추출 (topic, frequency, importance, description)
- 교재별 특징 및 장단점
- 공부 시간대, 집중력 관리 방법
- 취약 과목 극복 방법
**추천 교재 추출 규칙**:
- "추천 교재" 카테고리에 명시된 교재만 사용
- 교재명과 출판사가 모두 확인될 때만 포함
- 정보가 부족하면 recommended_books를 빈 배열로 반환
- "교재명", "책 제목" 같은 자리표시는 절대 사용하지 않음
- 교재 구매 링크(yes24, 알라딘, 교보문고 등)가 검색 결과에 있으면 url 필드에 포함
- 공식 홈페이지에서 제공하는 공개 문제/기출문제가 있으면 학습 자료로 포함

**후기 추출 강화**:
- 시험장에서 주의할 점 (시간 배분, 순서 등)
- 공부하면서 겪는 구체적인 어려움과 해결책
- 시험 전날/당일 준비사항
- 멘탈 관리, 슬럼프 극복 방법
- 합격 후 실무에서 활용하는 팁

**연봉 정보 추출 규칙** ⭐중요:
- 신뢰할 수 있는 출처만 사용: 통계청, 고용노동부, 워크넷, 잡코리아, 사람인 채용공고
- 검색 결과에 출처가 명시된 경우만 저장
- 형식: "신입 기준 연 2,800만원 ~ 3,500만원" 또는 "경력 3년 기준 연 4,000만원 ~ 5,000만원"
- 출처 없이 추측하지 마세요 - 불확실하면 null
- 직종/경력별 범위가 다르면 가장 일반적인 신입 기준 사용

**공식 출처 정보**:
- official_site: 시험 일정, 접수 공지를 확인할 수 있는 공식 사이트
- reference_urls에 시험 일정 페이지 URL 포함
- 사용자는 이 링크를 통해 최신 일정을 확인해야 함

**[취업준비생 관점 정보 추출 규칙]** ⭐NEW:

1. **채용 시장 정보 (job_market_info)**:
   - "8. 채용공고 정보" 카테고리 참고
   - job_posting_frequency: 채용공고 출현 빈도 ("매우 많음", "많음", "보통", "적음")
   - preferred_industries: 이 자격증을 선호하는 산업군 (예: ["IT", "금융", "제조"])
   - requirement_type: 채용 시 자격증 요건 유형 ("필수", "우대", "가산점")
   - public_sector_points: 공무원/공기업 가산점 (예: "5%", "3점")

2. **비용 상세 (cost_breakdown)**:
   - "10. 비용 정보" 카테고리 참고
   - exam_fee: 응시료 (예: "필기 19,400원 + 실기 22,600원")
   - exam_fee_refund: 환불 정책 (예: "시험 3일 전까지 100% 환불")
   - textbook_cost: 교재 비용 범위 (예: "30,000 ~ 50,000원")
   - lecture_cost: 인강 비용 범위 (예: "100,000 ~ 300,000원")
   - free_resources: 무료 학습 자료 (예: ["큐넷 기출문제", "유튜브 무료 강의"])

3. **합격 가능성 정보 (feasibility_info)**:
   - "11. 비전공자 합격 후기" 카테고리 참고
   - non_major_pass_rate: 비전공자 합격률 추정 (예: "약 30-35%")
   - self_study_possible: 독학 가능 여부 (true/false)
   - minimum_study_period: 최소 합격 준비기간 (일 단위, 예: 30)
   - first_attempt_pass_rate: 1회 합격 비율 (예: "약 40%")

4. **시험 일정 상세 (exam_schedule_detail)** ⭐중요:
   - **공식 출처(q-net.or.kr, .go.kr)에서 크롤링으로 확인된 경우만 저장**
   - 확인되지 않으면 반드시 null로 저장 (추측하지 마세요)
   - annual_exam_count: 연간 시험 횟수 (공식 확인된 경우만)
   - exam_type: 시험 유형 ("CBT", "정기", "CBT+정기")
   - next_exam_date: 가장 가까운 시험일 (예: "2026-03-15", 공식 출처에서 확인된 경우만)
   - registration_period: 접수 기간 (예: "2026-02-01 ~ 2026-02-07", 공식 출처에서 확인된 경우만)
   - result_announcement: 합격 발표일 또는 기준 (예: "2026-04-05" 또는 "시험 후 2주 내")

5. **유사 자격증 비교 (similar_certificates)**:
   - "13. 비교 정보" 카테고리 참고
   - 같은 분야의 비슷한 자격증과 비교
   - title: 유사 자격증명 (예: "정보처리산업기사")
   - comparison: 비교 설명 (예: "기사보다 난이도 낮음, 실무 경력 대신 취득 가능")

난이도 기준 및 study_period_days 정합성 규칙 ⭐필수:
- difficulty=1: study_period_days 1~21일 범위 (1~3주, 누구나 쉽게 합격 가능)
- difficulty=2: study_period_days 14~90일 범위 (2주~3개월, 기초 지식으로 합격 가능)
- difficulty=3: study_period_days 60~210일 범위 (2~7개월, 체계적 학습 필요)
- difficulty=4: study_period_days 150~540일 범위 (5개월~1.5년, 전문 지식 및 집중 학습 필요)
- difficulty=5: study_period_days 300~1095일 범위 (10개월~3년, 매우 높은 난이도, 장기 준비 필수)
⚠️ difficulty와 study_period_days는 반드시 위 범위가 일치해야 합니다. 범위를 벗어나면 difficulty를 study_period_days에 맞게 조정하세요.

출력은 반드시 유효한 JSON 형식으로 작성하세요.
**중요: JSON 문자열 내 줄바꿈은 반드시 \\n 이스케이프 시퀀스를 사용하세요. 실제 줄바꿈 문자를 사용하면 안 됩니다.**

{{
  "overview_draft": "1-2문장 초안 (줄바꿈 필요시 \\n 사용)",
  "difficulty": 1-5,
  "study_period_days": 일수 (실제 합격자 평균 준비기간),
  "exam_info": {{
    "subjects": ["과목1 (문항수, 시간)", "과목2 (문항수, 시간)", ...],
    "exam_type": "필기/실기/필기+실기/면접 (CBT/OMR/실기)",
    "passing_criteria": "합격 기준 (평균 60점 이상, 과목당 40점 이상 등)",
    "total_fee": 응시료 또는 null,
    "exam_structure": "시험 구성 설명 (예: 필기 100문항 2시간 30분, 실기 4시간 등)",
    "recent_trends": "최근 출제 경향 (예: 최신 기술 동향 반영, 실무 위주 출제 등)",
    "pass_rate_trend": "합격률 추이 (예: 2023년 45%, 2024년 48%, 2025년 50% - 상승 추세) 또는 null",
    "acquisition_method": "취득 방법 (예: '응시자격: 관련학과 졸업 또는 경력 2년 이상\\n취득절차: 필기시험 → 실기시험 → 자격증 발급')",
    "exam_criteria_url": "출제 기준 공식 링크 또는 null"
  }},
  "career_info": {{
    "use_cases": ["활용 분야1", "활용 분야2", ...],
    "related_jobs": ["관련 직업1", "관련 직업2", ...],
    "average_salary": "평균 연봉 범위 (예: 연 3,000만원 ~ 5,000만원)",
    "job_prospects": "취업 전망 2-3문장 서술 (현재 상황, 향후 전망, 구체적 이유 포함)",
    "industry": ["관련 산업1", "관련 산업2", ...]
  }},
  "user_reviews": {{
    "summary": "합격자 후기 요약 1-2문단 서술 (전반적 평가, 구체적 사례, 공통 의견 포함)",
    "difficulty_feedback": "난이도 평가 1-2문장 서술 (체감 난이도와 그 이유)",
    "difficulty_breakdown": {{"overall": 3, "written": 2, "practical": 4, "interview": null}},
    "study_tips": [
      "기출문제를 최소 3회 이상 반복해서 풀면 정답률이 90% 이상으로 올라갑니다.",
      "시험장에서 어려운 문제가 나오면 표시해두고 나중에 다시 풀어보는 것이 시간 관리에 효과적입니다.",
      "오답노트를 작성하면서 틀린 이유를 분석하고 개념을 다시 정리하면 같은 실수를 방지할 수 있습니다."
    ],
    "common_challenges": [
      "방대한 학습 분량이 부담스러울 수 있는데, 주차별 학습 계획을 세우고 매일 진도를 체크하면 효과적으로 관리할 수 있습니다.",
      "시험 당일 긴장감으로 실력 발휘가 어려울 수 있으므로, 시험 전 심호흡을 하고 편안한 옷을 착용하는 것이 도움됩니다.",
      "암기 과목이 많아 지치기 쉬운데, 반복 학습과 연상 기억법을 활용하면 효율적으로 암기할 수 있습니다."
    ],
    "exam_day_tips": [
      "시험 전날에는 새로운 내용을 학습하지 말고 그동안 공부한 핵심 개념만 가볍게 복습하세요.",
      "시험 당일에는 신분증, 수험표, 필기구를 반드시 챙기고 여유 있게 시험장에 도착하세요.",
      "시험 중 긴장되면 잠시 눈을 감고 심호흡을 3회 정도 하면 마음이 안정됩니다."
    ]
  }},
  "study_guide": {{
    "study_methods": [
      "방법1: 구체적 설명 (예: 교재 1회독 후 기출문제 풀이)",
      "방법2: 실제 합격자 방법 (예: 강의 1.5배속 수강 후 요약 노트 작성)",
      ...
    ],
    "key_exam_topics": [
      {{
        "topic": "소프트웨어 설계",
        "frequency": "매우 자주",
        "importance": "상",
        "description": "UML, 디자인 패턴, 요구사항 분석 등"
      }},
      {{
        "topic": "데이터베이스",
        "frequency": "자주",
        "importance": "상",
        "description": "SQL, 정규화, 인덱스 등"
      }}
    ],
    "time_allocation": {{
      "theory": "30% (이론 학습, 개념 이해)",
      "practice": "60% (기출문제, 모의고사 풀이)",
      "review": "10% (오답 복습, 취약 과목 보강)"
    }},
    "recommended_books": [
      {{
        "title": "정보처리기사 필기",
        "publisher": "출판사",
        "type": "필기/실기/종합",
        "description": "교재 특징 및 장단점 (예: 설명이 자세하나 두꺼움, 요약 위주로 빠른 학습 가능 등)",
        "url": "https://www.yes24.com/... 또는 null (구매 링크)"
      }},
      {{
        "title": "큐넷 공식 기출문제",
        "publisher": "한국산업인력공단",
        "type": "기출문제",
        "description": "공식 홈페이지에서 제공하는 공개 문제입니다. 무료로 다운로드 가능합니다.",
        "url": "https://www.q-net.or.kr/crf005.do?id=crf00505 (공식 기출 링크)"
      }}
    ],
    "success_tips": [
      "기출문제를 3회 이상 반복해서 풀고, 정답률 90%를 목표로 학습하면 실전에서 자신감이 생깁니다.",
      "틀린 문제는 오답노트에 정리하고 왜 틀렸는지 분석한 뒤 다시 풀어보면 같은 유형에서 실수를 줄일 수 있습니다.",
      "스터디 그룹을 만들어 주 1회 모의고사를 함께 풀고 토론하면 혼자 공부할 때 놓치는 부분을 보완할 수 있습니다.",
      "50분 공부 후 10분 휴식하는 패턴으로 집중력을 유지하고, 오전 시간대에 어려운 과목을 공부하면 효율이 높아집니다.",
      "취약 과목에는 다른 과목보다 2배 이상의 시간을 투자하여 평균 점수 이상으로 끌어올리는 것이 합격의 핵심입니다."
    ]
  }},
  "official_sources": {{
    "official_site": "시험 일정 및 접수를 확인할 수 있는 공식 사이트 URL (필수)",
    "issuing_organization": "발급 기관",
    "reference_urls": [
      "시험 일정 공지 페이지 URL",
      "시험 접수 페이지 URL",
      "기출문제 다운로드 URL",
      ...
    ]
  }},
  "lectures": [
    {{
      "platform": "플랫폼명",
      "title": "강의명 (반드시 {certificate_title} 관련)",
      "url": "검색 결과의 실제 URL",
      "instructor": "강사명 또는 null",
      "price": "가격 문자열 (예: '150000원', '무료', '50만원') 또는 null"
    }}
  ],
  "job_market_info": {{
    "job_posting_frequency": "채용공고 빈도 ('매우 많음', '많음', '보통', '적음') 또는 null",
    "preferred_industries": ["선호 산업1", "선호 산업2", ...],
    "requirement_type": "채용 요건 유형 ('필수', '우대', '가산점') 또는 null",
    "public_sector_points": "공무원/공기업 가산점 또는 null"
  }},
  "cost_breakdown": {{
    "exam_fee": "응시료 (예: '필기 19,400원 + 실기 22,600원')",
    "exam_fee_refund": "환불 정책 또는 null",
    "textbook_cost": "교재 비용 범위 또는 null",
    "lecture_cost": "인강 비용 범위 또는 null",
    "free_resources": ["무료 자료1", "무료 자료2", ...]
  }},
  "feasibility_info": {{
    "non_major_pass_rate": "비전공자 합격률 추정 또는 null",
    "self_study_possible": true/false 또는 null,
    "minimum_study_period": 최소 준비기간(일) 또는 null,
    "first_attempt_pass_rate": "1회 합격 비율 또는 null"
  }},
  "exam_schedule_detail": {{
    "annual_exam_count": 연간 시험 횟수 또는 null,
    "exam_type": "시험 유형 ('CBT', '정기', 'CBT+정기') 또는 null",
    "next_exam_date": null,
    "registration_period": null,
    "result_announcement": "일반적 발표 기준 (예: '시험 후 2주 내') 또는 null"
  }},
  "similar_certificates": [
    {{
      "title": "유사 자격증명",
      "comparison": "비교 설명 (예: '기사보다 난이도 낮음')"
    }}
  ]
}}
"""
        system_prompt = system_prompt.replace("{{", "{").replace("}}", "}")
        system_prompt = system_prompt.replace("{certificate_title}", certificate_title)

        user_prompt = search_context

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                # temperature를 지원하지 않는 모델 처리
                temperature = 0.2 + (attempt * 0.1)  # 재시도 시 온도 약간 증가
                params = self.build_completion_params(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                response = await self.client.chat.completions.create(**params)

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty response from LLM (Phase 1)")

                data = json.loads(content)
                study_guide = data.get("study_guide", {})
                if isinstance(study_guide, dict):
                    books = study_guide.get("recommended_books", [])
                    study_guide["recommended_books"] = self.sanitize_recommended_books(
                        books
                    )
                return Phase1Extraction(**data)

            except BadRequestError as e:
                last_error = e
                # JSON 검증 실패 시 failed_generation에서 복구 시도
                error_body = getattr(e, "body", {}) or {}
                if isinstance(error_body, dict):
                    failed_gen = error_body.get("error", {}).get(
                        "failed_generation", ""
                    )
                    if failed_gen:
                        print(
                            f"    [Phase 1] JSON 복구 시도 중... (시도 {attempt + 1}/{MAX_RETRIES + 1})"
                        )
                        repaired_data = self._try_repair_json(failed_gen)
                        if repaired_data:
                            try:
                                study_guide = repaired_data.get("study_guide", {})
                                if isinstance(study_guide, dict):
                                    books = study_guide.get("recommended_books", [])
                                    study_guide["recommended_books"] = (
                                        self.sanitize_recommended_books(books)
                                    )
                                return Phase1Extraction(**repaired_data)
                            except Exception:
                                pass  # 복구 실패, 재시도
                if attempt < MAX_RETRIES:
                    print(
                        f"    [Phase 1] 재시도 중... ({attempt + 2}/{MAX_RETRIES + 1})"
                    )
                    continue
                raise last_error

            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    print(
                        f"    [Phase 1] 오류 발생, 재시도 중... ({attempt + 2}/{MAX_RETRIES + 1}) [model: {self.model}]"
                    )
                    print(f"    [Phase 1] 오류 내용: {e}")
                    continue
                print(f"    [Phase 1] 최종 오류: {e}")
                raise last_error

        raise last_error or ValueError("Unknown error in Phase 1")

    async def _phase2_refine(
        self, certificate_title: str, extracted: Phase1Extraction
    ) -> CertificateEnrichment:
        """2단계: 추출 데이터를 정제하고 보강합니다."""

        system_prompt = f"""당신은 한국 자격증 정보 정제 전문가입니다.
추출된 정보를 바탕으로 정리만 하세요. 새로운 정보를 창작하거나 추측하지 마세요.
검색 결과에 없는 내용은 절대 추가하지 마세요.

자격증명: {certificate_title}

정제 규칙:
1. **서술형 작성**: 단답형 절대 금지, 읽기 쉬운 문장으로
2. **JSON 줄바꿈**: 문자열 내 줄바꿈은 반드시 \\n 이스케이프 시퀀스 사용 (실제 엔터 금지)
3. overview: 3-5문장, 문장 사이에 \\n 삽입
4. job_prospects: 4-5문장, \\n으로 구분
5. user_reviews.summary: 1-2문단, 문단 사이에 \\n\\n 삽입
6. 강의는 실제 강의 사이트만 (커뮤니티 제외)
7. 관련성 점수 0.5 미만 제외

**[문체 규칙 - 필수]** ⭐중요:
- 모든 서술형 텍스트는 존댓말(~입니다, ~합니다, ~됩니다)로 작성하세요.
- "~이다", "~한다", "~좋다" 등 반말 종결어미는 절대 사용하지 마세요.
- 친절하고 정중한 어조로 작성하세요.
- 예시:
  - 좋음: "이 자격증은 IT 분야에서 필수적입니다."
  - 나쁨: "이 자격증은 IT 분야에서 필수이다." (반말 금지)

**개요(overview) 작성 규칙**:
- 각 문장은 독립적으로 주어를 포함해야 합니다.
- "이 자격증은", "해당 자격증" 같은 지시어 사용을 피해주세요.
- 매 문장마다 자격증명 또는 구체적 주어를 사용하세요.
- 예시:
  - 좋음: "정보처리기사는 IT 분야 국가기술자격증입니다.\\n정보시스템의 분석, 설계, 개발 업무를 담당합니다.\\n소프트웨어 개발 전반의 전문성을 인증합니다."
  - 나쁨: "정보처리기사는 IT 전문가이다.\\n이 자격증은 개발 업무에 필수이다." (반말 금지)

**시험 정보 강화 규칙**:
- exam_structure: 필기/실기 구성, 총 문항수, 시험 시간 명시
- subjects: 각 과목명에 문항수 및 시간 추가 (예: "소프트웨어 설계 (20문항, 30분)")
- recent_trends: 최근 3년간 출제 경향 분석, 자주 나오는 주제 3가지 이상

**학습 가이드 강화 규칙**:
- study_methods: 실제 합격자들의 구체적인 방법 5가지 이상
- key_exam_topics: 핵심 출제 토픽 5개 이상 (topic, frequency, importance, description 포함)
- success_tips: 구체적이고 실행 가능한 팁 7가지 이상
**추천 교재 규칙**:
- 교재명과 출판사 정보가 명확한 경우에만 포함
- 정보가 부족하면 recommended_books는 빈 배열
- 교재 구매 링크(yes24, 알라딘, 교보문고)가 있으면 url 필드에 포함
- 공식 홈페이지 공개 문제/기출문제가 있으면 반드시 포함 (type: "기출문제")

**후기 강화 규칙**:
- study_tips: 실전 팁 포함 (시험장 노하우, 시간 배분 전략)
- common_challenges: 각 어려움에 대한 구체적 해결책 포함
- exam_day_tips 필수: 시험 전날, 당일 준비사항 3가지 이상
- difficulty_breakdown 구조 유지

**공식 출처 필수 규칙**:
- official_site: 반드시 포함, 시험 일정 및 접수 확인 가능한 링크
- reference_urls: 시험 일정 공지 페이지 URL 최우선 포함

**연봉 정보 규칙** ⭐중요:
- 신뢰할 수 있는 출처(통계청, 고용노동부, 워크넷, 잡코리아, 사람인)에서 확인된 경우만
- 형식: "신입 기준 연 2,800만원 ~ 3,500만원" (경력/직종 기준 명시)
- 출처 없이 추측 금지 - 불확실하면 null

**[취업준비생 관점 정제 규칙]** ⭐NEW:

1. **채용 시장 정보 (job_market_info)**:
   - job_posting_frequency: 구체적 빈도 ("매우 많음", "많음", "보통", "적음")
   - preferred_industries: 최소 3개 이상의 산업군 나열
   - requirement_type: "필수", "우대", "가산점" 중 가장 일반적인 유형
   - public_sector_points: 공무원/공기업 가산점 구체적으로 (예: "필기 5점, 면접 3점")

2. **비용 상세 (cost_breakdown)**:
   - exam_fee: 필기+실기 각각 분리해서 명시 (예: "필기 19,400원 + 실기 22,600원")
   - free_resources: 무료 학습 자료 최소 3개 이상 (유튜브, 큐넷, 블로그 등)

3. **합격 가능성 정보 (feasibility_info)**:
   - non_major_pass_rate: 비전공자 합격률 범위 (예: "약 25-35%")
   - self_study_possible: 독학 가능 여부와 근거 포함
   - minimum_study_period: 최소 준비기간 일수 (빠른 합격자 기준)

4. **시험 일정 상세 (exam_schedule_detail)** ⭐중요:
   - annual_exam_count: 공식 출처에서 확인된 연간 횟수만
   - exam_type: CBT/정기/상시 구분 명확히
   - next_exam_date: **null 유지** (시험 일정은 변동이 많아 추측하지 마세요)
   - registration_period: **null 유지** (접수 기간은 변동이 많아 추측하지 마세요)
   - 사용자는 반드시 공식 사이트에서 최신 일정을 확인해야 합니다

5. **유사 자격증 비교 (similar_certificates)**:
   - 같은 분야 자격증 2-3개 비교
   - comparison: 난이도, 활용도, 준비기간 차이 설명

강의 관련성 점수 기준:
- 1.0: 제목에 자격증명 정확히 포함 + 신뢰할 수 있는 플랫폼
- 0.8-0.9: 제목에 자격증명 유사 포함 + 신뢰할 수 있는 플랫폼
- 0.5-0.7: 제목에 자격증명 일부 포함
- 0.0-0.4: 다른 자격증 또는 관련 없음 (제외)

**강의 후기 페이지 제외 규칙** ⭐중요:
- 강의 사이트의 수강 후기 페이지는 추천 강의에서 제외합니다.
- URL에 "review", "후기", "평가" 등이 포함된 페이지는 제외합니다.
- 실제 강의 수강 페이지(강좌 소개, 커리큘럼)만 포함합니다.

출력은 반드시 유효한 JSON 형식으로 작성하세요.
**중요: JSON 문자열 내 줄바꿈은 반드시 \\n 이스케이프 시퀀스를 사용하세요. 실제 줄바꿈 문자를 사용하면 안 됩니다.**

예시:
{{
  "overview": "세무사는 세무 관련 전문가입니다.\\n이 자격증은 세무 업무에 필수적입니다.\\n기업과 개인의 세무 관리를 담당합니다.",
  "difficulty": 3,
  "study_period_days": 180,
  "exam_info": {{
    "subjects": ["세법학 1부 (25문항, 50분)", "세법학 2부 (25문항, 50분)"],
    "exam_type": "필기 (CBT)",
    "passing_criteria": "평균 60점 이상, 과목당 40점 이상",
    "total_fee": "100000",
    "exam_structure": "1차 필기 100문항 2시간 30분, 2차 실무 4과목 각 2시간",
    "recent_trends": "최근 3년간 세법 개정 내용 출제 빈도 증가, 실무 사례 중심 문제 출제",
    "pass_rate_trend": "2023년 15%, 2024년 18%, 2025년 20% - 상승 추세"
  }},
  "career_info": {{
    "use_cases": ["세무법인", "회계법인", "기업 세무팀"],
    "related_jobs": ["세무사", "회계사", "세무 컨설턴트"],
    "average_salary": "연 3,000만원 ~ 5,000만원",
    "job_prospects": "현재 세무사 수요는 꾸준합니다.\\n세법 개정으로 인해 향후 전망이 밝습니다.\\n중소기업 대상 시장이 확대되고 있습니다.",
    "industry": ["세무", "회계", "금융"]
  }},
  "user_reviews": {{
    "summary": "합격자들은 난이도가 높다고 평가합니다.\\n\\n실제 합격자들은 1-2년의 준비 기간을 권장합니다.",
    "difficulty_feedback": "난이도가 매우 높습니다.\\n방대한 학습량과 복잡한 세법이 주요 원인입니다.",
    "difficulty_breakdown": {{"overall": 5, "written": 4, "practical": 5, "interview": null}},
    "study_tips": [
      "기출문제를 3회 이상 반복해서 풀면 정답률 90% 이상 도달이 가능하며, 자주 출제되는 유형을 파악할 수 있습니다.",
      "시험장에서 어려운 문제가 나오면 표시해두고 나중에 다시 풀면 시간 관리에 효과적입니다.",
      "오답노트를 작성하면서 틀린 이유를 분석하고 개념을 다시 정리하면 같은 실수를 방지할 수 있습니다."
    ],
    "common_challenges": [
      "방대한 학습 분량이 부담스러울 수 있는데, 주차별 학습 계획을 세우고 매일 진도를 체크하면 효과적으로 관리할 수 있습니다.",
      "시험 당일 긴장감으로 실력 발휘가 어려울 수 있으므로, 시험 전날 충분히 수면을 취하고 당일 간단한 스트레칭을 하면 도움됩니다.",
      "암기 과목이 많아 지치기 쉬운데, 반복 학습과 연상 기억법을 활용하면 효율적으로 암기할 수 있습니다."
    ],
    "exam_day_tips": [
      "시험 전날에는 새로운 내용을 학습하지 말고 그동안 공부한 핵심 개념만 가볍게 복습하세요.",
      "시험 당일에는 계산기, 신분증, 수험표를 반드시 챙기고 여유 있게 시험장에 도착하세요.",
      "시험 중 긴장되면 잠시 눈을 감고 심호흡을 3회 정도 하면서 긍정적인 자기 암시를 해보세요."
    ]
  }},
  "study_guide": {{
    "study_methods": [
      "교재를 3회 반복해서 학습하면 효과적인데, 1회독은 이해 위주로, 2회독은 암기 위주로, 3회독은 정리 위주로 진행하세요.",
      "기출문제를 중심으로 학습하면서 최근 5개년 문제를 3회 반복해서 풀면 출제 경향을 파악할 수 있습니다.",
      "강의를 1.5배속으로 수강한 후 요약 노트를 작성하면 복습 시간을 단축할 수 있습니다.",
      "스터디 그룹을 만들어 주 1회 모의고사를 함께 풀고 취약 과목에 대해 토론하면 혼자 공부할 때 놓치는 부분을 보완할 수 있습니다.",
      "온라인 무료 강의를 활용하면 비용을 절감하면서 복습용으로 효과적으로 사용할 수 있습니다."
    ],
    "key_exam_topics": [
      {{"topic": "세법학 1부", "frequency": "매우 자주", "importance": "상", "description": "국세기본법, 소득세법, 법인세법"}},
      {{"topic": "세법학 2부", "frequency": "매우 자주", "importance": "상", "description": "부가가치세법, 상속세 및 증여세법"}},
      {{"topic": "회계학", "frequency": "자주", "importance": "상", "description": "재무회계, 원가회계, 세무회계"}},
      {{"topic": "재정학", "frequency": "보통", "importance": "중", "description": "조세론, 재정정책"}},
      {{"topic": "민법", "frequency": "보통", "importance": "중", "description": "민법총칙, 물권법, 채권법"}}
    ],
    "time_allocation": {{
      "theory": "30% (이론 학습, 개념 이해)",
      "practice": "60% (기출문제, 모의고사 풀이)",
      "review": "10% (오답 복습, 취약 과목 보강)"
    }},
    "recommended_books": [
      {{
        "title": "세무사 1차 필기",
        "publisher": "에듀윌",
        "type": "필기",
        "description": "설명이 자세하나 두꺼움, 초보자 추천",
        "url": "https://www.yes24.com/Product/Goods/12345"
      }},
      {{
        "title": "세무사 요약집",
        "publisher": "해커스",
        "type": "종합",
        "description": "요약 위주로 빠른 학습 가능, 2-3회독 후 사용 권장",
        "url": "https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=12345"
      }},
      {{
        "title": "큐넷 공식 기출문제",
        "publisher": "한국산업인력공단",
        "type": "기출문제",
        "description": "공식 홈페이지에서 제공하는 공개 문제입니다. 무료로 다운로드 가능합니다.",
        "url": "https://www.q-net.or.kr/crf005.do?id=crf00505"
      }}
    ],
    "success_tips": [
      "기출문제를 3회 이상 반복해서 풀고, 정답률 90%를 목표로 학습하면 실전에서 자신감이 생깁니다.",
      "틀린 문제는 오답노트에 정리하고 왜 틀렸는지 분석한 뒤 다시 풀어보면 같은 유형에서 실수를 줄일 수 있습니다.",
      "스터디 그룹을 만들어 주 1회 모의고사를 함께 풀고 토론하면 혼자 공부할 때 놓치는 부분을 보완할 수 있습니다.",
      "50분 공부 후 10분 휴식하는 패턴으로 집중력을 유지하고, 오전 시간대에 어려운 과목을 공부하면 효율이 높아집니다.",
      "취약 과목에는 다른 과목보다 2배 이상의 시간을 투자하여 평균 점수 이상으로 끌어올리는 것이 합격의 핵심입니다.",
      "슬럼프가 올 때는 1-2일 정도 쉬면서 리프레시한 후 다시 공부를 시작하면 효율이 더 좋아집니다.",
      "시험 2주 전부터는 실제 시험 시간에 맞춰 모의고사를 풀면서 실전 감각을 익히는 것이 중요합니다."
    ]
  }},
  "official_sources": {{
    "official_site": "https://www.q-net.or.kr (시험 일정 및 접수 확인)",
    "issuing_organization": "한국산업인력공단",
    "reference_urls": [
      "https://www.q-net.or.kr/site/tax/schedule.do (시험 일정 공지)",
      "https://www.q-net.or.kr/site/tax/apply.do (시험 접수)",
      "https://www.q-net.or.kr/site/tax/pastexam.do (기출문제 다운로드)"
    ]
  }},
  "recommended_lectures": [...],
  "job_market_info": {{
    "job_posting_frequency": "많음",
    "preferred_industries": ["세무법인", "회계법인", "금융업", "대기업 재무팀", "공기업"],
    "requirement_type": "우대",
    "public_sector_points": "국세청 5%, 지방세 담당 공무원 가산점"
  }},
  "cost_breakdown": {{
    "exam_fee": "1차 필기 30,000원 + 2차 실무 50,000원 = 총 80,000원",
    "exam_fee_refund": "시험 7일 전까지 100% 환불 가능",
    "textbook_cost": "50,000 ~ 150,000원 (기본서 + 문제집)",
    "lecture_cost": "300,000 ~ 1,500,000원 (인강 1년 기준)",
    "free_resources": ["큐넷 기출문제", "유튜브 세무사 강의", "국세청 세법 자료"]
  }},
  "feasibility_info": {{
    "non_major_pass_rate": "약 15-20% (전체 합격률보다 낮음)",
    "self_study_possible": false,
    "minimum_study_period": 365,
    "first_attempt_pass_rate": "약 10%"
  }},
  "exam_schedule_detail": {{
    "annual_exam_count": 1,
    "exam_type": "정기시험 (연 1회)",
    "next_exam_date": null,
    "registration_period": null,
    "result_announcement": "1차: 시험 후 약 1개월, 2차: 시험 후 약 3개월 (공식 사이트에서 최신 일정 확인 필요)"
  }},
  "similar_certificates": [
    {{
      "title": "공인회계사(CPA)",
      "comparison": "세무사보다 난이도 높음, 회계 감사 업무 가능, 준비기간 2-3년"
    }},
    {{
      "title": "세무회계 1급",
      "comparison": "세무사보다 난이도 낮음, 민간자격, 실무 입문용으로 적합"
    }},
    {{
      "title": "전산세무 1급",
      "comparison": "실무 중심 자격증, 세무사 준비 전 실습용으로 좋음"
    }}
  ]
}}

**핵심 규칙**:
1. **JSON 문자열 내 줄바꿈은 반드시 \\n 이스케이프 시퀀스 사용** (실제 줄바꿈 문자 금지)
2. **difficulty 필수** ⭐절대생략금지: 1-5 범위 정수 (정보 없으면 3 사용)
3. **study_period_days 필수** ⭐절대생략금지: 준비기간 일수 (정보 없으면 90 사용)
4. **difficulty-study_period_days 정합성** ⭐필수: 아래 범위를 반드시 일치시키세요.
   - difficulty=1 → study_period_days 1~21일
   - difficulty=2 → study_period_days 14~90일
   - difficulty=3 → study_period_days 60~210일
   - difficulty=4 → study_period_days 150~540일
   - difficulty=5 → study_period_days 300~1095일
5. exam_info는 구체적으로 (문항수, 시간, 출제 경향)
6. study_guide는 key_exam_topics 포함 (핵심 출제 토픽 5개 이상)
7. user_reviews.exam_day_tips 필수 (시험 전날, 당일, 멘탈 관리)
8. official_sources.reference_urls에 시험 일정 페이지 필수 포함
9. job_prospects는 4-5문장, \\n으로 구분:
   - 첫 문장: 해당 자격증의 현재 취업 시장 수요
   - 둘째 문장: 필수/우대로 요구하는 대표 직무 (예: "SI 개발자, 솔루션 엔지니어 채용 시 필수")
   - 셋째 문장: 대표 기업 사례 (예: "삼성SDS, LG CNS, 네이버 등 IT 대기업에서 우대")
   - 넷째 문장: 향후 전망 및 성장 가능성
   - 다섯째 문장: 커리어 상승 효과 (있으면)
10. user_reviews.summary는 문단 2개, \\n\\n으로 구분
11. 모든 필드 값이 완전한 JSON 문자열로 닫혀 있는지 확인
"""

        user_prompt = f"""추출된 데이터:
{extracted.model_dump_json(indent=2)}

위 데이터를 정제하고 완성도를 높여주세요.
특히 overview를 3-5문장으로 확장하고, 강의는 관련성 점수를 계산하여 0.5 미만은 제외하세요.
**중요: 모든 문자열 값은 유효한 JSON 형식이어야 합니다. 줄바꿈은 \\n을 사용하세요.**"""

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                # temperature를 지원하지 않는 모델 처리
                temperature = 0.1 + (attempt * 0.05)  # 창의성 제거: 낮은 온도 유지
                params = self.build_completion_params(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    response_format={"type": "json_object"},
                )
                response = await self.client.chat.completions.create(**params)

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty response from LLM (Phase 2)")

                data = json.loads(content)
                study_guide = data.get("study_guide", {})
                if isinstance(study_guide, dict):
                    books = study_guide.get("recommended_books", [])
                    study_guide["recommended_books"] = self.sanitize_recommended_books(
                        books
                    )
                return CertificateEnrichment(**data)

            except BadRequestError as e:
                last_error = e
                # JSON 검증 실패 시 failed_generation에서 복구 시도
                error_body = getattr(e, "body", {}) or {}
                if isinstance(error_body, dict):
                    failed_gen = error_body.get("error", {}).get(
                        "failed_generation", ""
                    )
                    if failed_gen:
                        print(
                            f"    [Phase 2] JSON 복구 시도 중... (시도 {attempt + 1}/{MAX_RETRIES + 1})"
                        )
                        repaired_data = self._try_repair_json(failed_gen)
                        if repaired_data:
                            try:
                                study_guide = repaired_data.get("study_guide", {})
                                if isinstance(study_guide, dict):
                                    books = study_guide.get("recommended_books", [])
                                    study_guide["recommended_books"] = (
                                        self.sanitize_recommended_books(books)
                                    )
                                return CertificateEnrichment(**repaired_data)
                            except Exception:
                                pass  # 복구 실패, 재시도
                if attempt < MAX_RETRIES:
                    print(
                        f"    [Phase 2] 재시도 중... ({attempt + 2}/{MAX_RETRIES + 1})"
                    )
                    continue
                raise last_error

            except Exception as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    print(
                        f"    [Phase 2] 오류 발생, 재시도 중... ({attempt + 2}/{MAX_RETRIES + 1}) [model: {self.model}]"
                    )
                    print(f"    [Phase 2] 오류 내용: {e}")
                    continue
                print(f"    [Phase 2] 최종 오류: {e}")
                raise last_error

        raise last_error or ValueError("Unknown error in Phase 2")


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """싱글턴 LLM 서비스 인스턴스를 반환합니다.

    Returns:
        LLMService 인스턴스.
    """
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
