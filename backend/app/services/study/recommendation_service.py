"""자격증 추천 서비스.

RAG (Retrieval-Augmented Generation) 기반 의미 검색 추천.
ChromaDB와 OpenAI 임베딩을 활용한 벡터 유사도 검색.

MariaDB(SQLAlchemy)로 마이그레이션됨 (2026-01-22).
"""

import hashlib
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.certificate import Certificate as CertificateModel
from app.schemas.certificate import Certificate
from app.schemas.recommendation import (
    Feasibility,
    QuickStats,
    RecommendationRequest,
    RecommendationResponse,
    RecommendedCertificate,
    StudyInsights,
)
from app.services.embedding.service import EmbeddingService
from app.services.embedding.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


STUDY_TIMELINE_DAYS: dict[str, int | None] = {
    "3개월 이하": 90,
    "6개월 이하": 180,
    "1년 이하": 365,
    "1년 이상": None,  # no upper bound
    "상관없음": None,  # no constraint
}

AVAILABLE_DAYS: dict[str, int] = {
    "3개월 이하": 90,
    "6개월 이하": 180,
    "1년 이하": 365,
    "1년 이상": 365 * 2,
    "상관없음": 365 * 2,
}

DIFFICULTY_LIMITS: dict[str, int | None] = {
    "쉬운 편": 2,
    "중간": 3,
    "어려워도 상관없음": None,
}

# 도메인-산업 매핑: 사용자 관심 분야 → 자격증 산업 키워드 매칭용
# VALID_INTEREST_DOMAINS와 일치하도록 키를 정의함 (recommendation.py 참조)
# 2026-02-06: 키워드 확장 - IT개발 분야 선택 시 무관 자격증 추천 방지
DOMAIN_INDUSTRY_MAPPING: dict[str, list[str]] = {
    # VALID_INTEREST_DOMAINS 기준
    "기획/전략": ["기획", "전략", "경영", "컨설팅", "PM", "사업개발"],
    "마케팅/홍보/조사": ["마케팅", "홍보", "광고", "브랜드", "리서치", "조사"],
    "회계/세무/재무": ["회계", "세무", "금융", "재무", "경리", "회계법인"],
    "인사/노무/HRD": ["인사", "노무", "HRD", "채용", "교육훈련", "인력개발"],
    "총무/법무/사무": ["총무", "법무", "사무", "행정", "비서", "문서관리"],
    "IT개발": [
        # 핵심 키워드
        "IT",
        "소프트웨어",
        "정보기술",
        "ICT",
        "정보통신",
        "컴퓨터",
        # 확장 키워드 (2026-02-06)
        "프로그래밍",
        "전자계산",
        "네트워크",
        "보안",
        "웹",
        "앱",
        "데이터베이스",
        "서버",
        "클라우드",
        "리눅스",
        "정보처리",
        "전산",
        # compound 키워드 (2026-02-08): "개발"/"시스템" 단독 → false positive 방지
        # "개발" → "해양플랜트 개발"(조선), "농촌 개발" 등에 매칭됨
        # "시스템" → "조선 시스템", "기계 시스템" 등에 매칭됨
        "소프트웨어개발",
        "시스템개발",
        "정보시스템",
        "웹개발",
        "앱개발",
    ],
    "데이터": ["데이터", "AI", "빅데이터", "분석", "인공지능", "머신러닝"],
    "디자인": [
        # 기존 키워드
        "디자인",
        "UX",
        "UI",
        "그래픽",
        "웹디자인",
        "시각디자인",
        # 확장 키워드 (2026-02-06)
        "편집디자인",
        "광고디자인",
        "제품디자인",
        "색채",
        "컬러리스트",
        "일러스트",
        "영상편집",
        "3D",
        "CAD",
    ],
    "영업/판매/무역": ["영업", "판매", "무역", "수출", "수입", "영업관리"],
    "고객상담/TM": ["고객상담", "TM", "CS", "콜센터", "상담", "고객서비스"],
    "구매/자재/물류": ["구매", "자재", "물류", "유통", "SCM", "창고"],
    "상품기획/MD": ["상품기획", "MD", "머천다이징", "바이어", "소싱"],
    "운전/운송/배송": ["운전", "운송", "배송", "택배", "물류", "드라이버"],
    "서비스": ["서비스", "관광", "호텔", "여행", "외식", "레저", "요식업"],
    "생산": ["생산", "제조", "공장", "품질관리", "생산관리", "제조업"],
    "건설/건축": ["건설", "건축", "토목", "시공", "설계", "인테리어"],
    "의료": [
        # 핵심 키워드
        "의료",
        "병원",
        "의약",
        "간호",
        "헬스케어",
        "의약품",
        # compound 키워드 (2026-02-08): "보건" 단독 → "안전보건"(산업안전) 등에 매칭됨
        "보건의료",
        "공중보건",
        "보건소",
        "의료기관",
        "약사",
        "약국",
        "치과",
        "한의",
        "임상",
        "의사",
    ],
    "연구/R&D": ["연구", "R&D", "개발", "연구소", "실험", "기술개발"],
    "교육": ["교육", "학원", "강사", "교사", "학습", "연수원", "훈련"],
    "미디어/문화/스포츠": [
        "미디어",
        "문화",
        "스포츠",
        "방송",
        "영상",
        "콘텐츠",
        "체육",
    ],
    "금융/보험": ["금융", "은행", "보험", "증권", "투자", "자산관리"],
    "공공/복지": ["공공", "복지", "사회복지", "정부", "지자체", "NGO"],
}

# 분야별 제외 키워드 (해당 키워드가 포함되면 필터에서 제외)
# 2026-02-06: 제외 키워드 확장 - IT개발 분야 선택 시 무관 자격증 추천 방지
DOMAIN_EXCLUSION_KEYWORDS: dict[str, list[str]] = {
    "의료": [
        # 기존 키워드
        "미용",
        "피부관리",
        "헤어",
        "네일",
        "메이크업",
        # 추가 제외 (2026-02-08): false positive 방지
        "안전보건",
        "산업안전",
        "농작업",
        "농업",
        "농촌",
        "축산",
        "조선",
        "선박",
        "토목",
        "건설현장",
    ],
    "IT개발": [
        # 기존 키워드
        "가공",
        "용접",
        "기계",
        # 확장 키워드 (2026-02-06)
        "금속",
        "목공",
        "제과",
        "조리",
        "미용",
        "관광",
        "수산",
        "기상",
        "호텔",
        # 추가 제외 (2026-02-08): false positive 방지
        "조선",
        "선박",
        "해양",
        "농업",
        "농작업",
        "농촌",
        "축산",
        "토목",
        "섬유",
        "피부",
        "네일",
        "양식",
        # 제조업 자격증 제외 (2026-02-11): "전기전자" industry 혼란 방지
        "전자부품",
        "전기기기",
        "전기설비",
        "전기공사",
        "전기철도",
        "금속재료",
        "금속가공",
        "기계가공",
        "기계설계",
        "기계조립",
        "산업안전",
        "건설안전",
        "화학분석",
        "세라믹",
        "플라스틱",
        "품질관리",
        "생산관리",
        "공조냉동",
        "용접",
        "주조",
    ],
    # 신규 분야 (2026-02-06)
    "데이터": ["가공", "용접", "기계가공", "금속", "제조", "수산", "기상"],
    "디자인": [
        "기계",
        "전기",
        "화학",
        "건설",
        "용접",
        "의료",
        "수산",
        "기상",
        "양식",
    ],
}

# 타임라인 표시 텍스트 매핑
TIMELINE_DISPLAY_TEXT: dict[str, str] = {
    "3개월 이하": "3개월",
    "6개월 이하": "6개월",
    "1년 이하": "1년",
    "1년 이상": "1년 이상",
    "상관없음": "",
}

# 현재 상황별 적합 난이도 매핑
STATUS_DIFFICULTY_MAPPING: dict[str, tuple[int, int]] = {
    "student": (1, 3),  # 학생: 입문~중급
    "entry_jobseeker": (1, 3),  # 신입 구직자: 입문~중급
    "junior_worker": (2, 4),  # 1-3년차: 중하~중상
    "senior_worker": (3, 5),  # 4년차 이상: 중급~고급
    "career_break": (1, 3),  # 휴직/전업준비: 입문~중급
}

# 투자 시간별 적합 준비 기간 매핑 (일 기준)
COMMITMENT_DAYS_MAPPING: dict[str, tuple[int, int]] = {
    "relaxed": (0, 90),  # 여유 있게: ~3개월
    "moderate": (0, 180),  # 적당히: ~6개월
    "intensive": (0, 365),  # 집중해서: ~1년
    "unsure": (0, 365 * 2),  # 잘 모르겠어요: 제한 없음
}

# 폴백 시 반환할 기본 결과 수
FALLBACK_COUNT = 5

# B7: config에서 로드 (하드코딩 제거)
_settings = get_settings()
MIN_SIMILARITY_SCORE = _settings.RECOMMENDATION_MIN_SIMILARITY_SCORE
RECOMMENDATION_TOP_K = _settings.RECOMMENDATION_TOP_K


class RecommendationService:
    """RAG 기반 자격증 추천을 생성하는 서비스."""

    def __init__(
        self,
        db: Session,
        embedding_service: Optional[EmbeddingService] = None,
        vector_store: Optional[VectorStoreService] = None,
    ):
        """SQLAlchemy 세션과 RAG 서비스로 초기화합니다.

        Args:
            db: SQLAlchemy 데이터베이스 세션.
            embedding_service: 임베딩 생성 서비스 (선택).
            vector_store: ChromaDB 벡터 스토어 서비스 (선택).
        """
        self.db = db
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or VectorStoreService()

    async def get_recommendations(
        self, request: RecommendationRequest
    ) -> RecommendationResponse:
        """RAG 기반 자격증 추천을 생성합니다.

        벡터 유사도 검색을 통해 사용자 맥락에 가장 적합한 자격증을 추천합니다.

        Args:
            request: 사용자 추천 요청(맥락 포함).

        Returns:
            매칭된 자격증과 이유를 담은 RecommendationResponse.
        """
        logger.info(f"[RAG] Generating recommendations for: {request.model_dump()}")

        constraints = self._build_constraints(request)

        # Step 1: Build query text from user context
        query_text = self._build_query_text(request)
        logger.info(f"[RAG] Query text: {query_text}")

        # Step 2: Search vector store using OpenAI Embedding
        # ChromaDB에서 OpenAI 임베딩으로 쿼리 텍스트를 자동으로 임베딩합니다
        similar_results = self.vector_store.search_records(
            namespace=VectorStoreService.NAMESPACE,
            query=query_text,
            top_k=RECOMMENDATION_TOP_K,  # B7: config에서 로드
            filter_dict=self._build_vector_filter(request),
        )
        logger.info(
            f"[RAG] Found {len(similar_results)} similar certificates (Integrated Embedding)"
        )

        similarity_results = self._filter_by_similarity(similar_results)

        if not similarity_results:
            # No results found above threshold
            return RecommendationResponse(
                recommendations=[],
                query_summary=self._generate_query_summary(request),
                user_summary=request.user_summary,
                total_matched=0,
            )

        # Step 4: Fetch full certificate data from MariaDB (동기 호출)
        cert_ids = [result["id"] for result in similarity_results]
        certificates = self._fetch_certificates_by_ids(cert_ids)
        logger.info(f"[RAG] Fetched {len(certificates)} full certificate records")

        # Step 4.5: Apply structured constraints (timeline/difficulty)
        constrained_certificates = self._apply_constraints(certificates, constraints)

        # Step 4.6: Apply domain-based hard filter (2026-02-06)
        # IT개발 분야 선택 시 미용사, 항공사진기능사 등 무관한 자격증 제외
        domain_filtered_certificates = self._apply_domain_filter(
            constrained_certificates, request
        )
        logger.info(
            f"[RAG] After applying domain filter: {len(domain_filtered_certificates)} certificates remain"
        )

        allowed_ids = {cert["id"] for cert in domain_filtered_certificates}
        filtered_results = [
            result for result in similarity_results if result["id"] in allowed_ids
        ]

        logger.info(
            f"[RAG] After applying all constraints: {len(filtered_results)} certificates remain"
        )

        # B3 수정: 제약조건에 맞는 결과가 없으면 빈 결과 반환 (폴백 제거)
        # 사용자가 선택한 제약조건을 무시하고 폴백하면 안 됨
        if not filtered_results:
            return RecommendationResponse(
                recommendations=[],
                query_summary=self._generate_query_summary(request),
                user_summary=request.user_summary,
                total_matched=0,
            )

        # Step 5: Generate recommendations with vector similarity scores
        recommendations = self._generate_recommendations_from_vector_results(
            filtered_results, domain_filtered_certificates, request, constraints
        )

        # Step 6: Generate query summary
        query_summary = self._generate_query_summary(request)

        return RecommendationResponse(
            recommendations=recommendations,  # Already filtered and sorted
            query_summary=query_summary,
            user_summary=request.user_summary,  # 사용자 원본 요청 전달
            total_matched=len(filtered_results),
        )

    def _filter_by_similarity(self, results: list[dict]) -> list[dict]:
        """유사도 점수 기반 필터링을 적용합니다.

        절대 최소 임계값(0.2)을 적용하여 관련 없는 자격증이 추천되지 않도록 합니다.
        MIN_SIMILARITY_SCORE(0.35) 이상 결과가 없으면, 절대 최소 임계값 이상인 경우에만 폴백합니다.
        """
        if not results:
            return []

        # 절대 최소 임계값: 이보다 낮으면 폴백도 하지 않음
        # OpenAI text-embedding-3-small 기준 0.2으로 조정
        # (코사인 유사도 범위가 BGE-M3보다 낮음)
        ABSOLUTE_MIN_SCORE = 0.2

        filtered_results = [
            result for result in results if result["score"] >= MIN_SIMILARITY_SCORE
        ]

        if filtered_results:
            logger.info(
                f"[RAG] After filtering (score >= {MIN_SIMILARITY_SCORE}): "
                f"{len(filtered_results)} certificates"
            )
            return filtered_results

        # MIN_SIMILARITY_SCORE 미만이지만 ABSOLUTE_MIN_SCORE 이상인 결과 확인
        top_result = max(results, key=lambda r: r["score"])

        if top_result["score"] < ABSOLUTE_MIN_SCORE:
            # 절대 최소 임계값 미만이면 폴백 없이 빈 결과 반환
            logger.info(
                f"[RAG] Top result score ({top_result['score']:.4f}) is below "
                f"absolute minimum ({ABSOLUTE_MIN_SCORE}). Returning empty results."
            )
            return []

        logger.info(
            f"[RAG] No matches above {MIN_SIMILARITY_SCORE}; "
            f"returning top result with score {top_result['score']:.4f} for fallback."
        )
        return [top_result]

    def _build_constraints(self, request: RecommendationRequest) -> dict[str, Any]:
        """사용자 입력을 기반으로 하드 필터 기준을 계산합니다."""
        return {
            "max_study_days": STUDY_TIMELINE_DAYS.get(request.study_timeline),
            "max_difficulty": DIFFICULTY_LIMITS.get(request.difficulty_preference),
        }

    def _apply_constraints(
        self,
        certificates: list[dict[str, Any]],
        constraints: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """타임라인/난이도 제약을 만족하는 자격증만 남깁니다."""
        max_days = constraints.get("max_study_days")
        max_difficulty = constraints.get("max_difficulty")

        filtered = []
        for cert in certificates:
            within_timeline = True
            within_difficulty = True

            if max_days is not None and cert.get("study_period_days"):
                within_timeline = cert["study_period_days"] <= max_days

            if max_difficulty is not None and cert.get("difficulty"):
                within_difficulty = cert["difficulty"] <= max_difficulty

            if within_timeline and within_difficulty:
                filtered.append(cert)

        return filtered

    def _apply_domain_filter(
        self,
        certificates: list[dict[str, Any]],
        request: RecommendationRequest,
    ) -> list[dict[str, Any]]:
        """관심 분야에 맞는 자격증만 필터링합니다.

        사용자가 선택한 interest_domains와 DOMAIN_INDUSTRY_MAPPING을 사용하여
        자격증의 title, overview, career_info.industry, job_market_info.preferred_industries,
        career_info.related_jobs와 매칭합니다.

        2026-02-06 수정:
        - 폴백 로직 제거: 매칭 결과 0개면 빈 리스트 반환 (무관 자격증 추천 방지)
        - 매칭 범위 확장: title, overview 추가

        Args:
            certificates: 자격증 딕셔너리 목록.
            request: 사용자 추천 요청.

        Returns:
            필터링된 자격증 목록. 매칭 결과 없으면 빈 리스트 반환.
        """
        if not request.interest_domains:
            return certificates

        # DOMAIN_INDUSTRY_MAPPING에서 관련 키워드 수집
        user_keywords = set()
        exclusion_keywords = set()
        for domain in request.interest_domains:
            keywords = DOMAIN_INDUSTRY_MAPPING.get(domain, [])
            user_keywords.update(kw.lower() for kw in keywords)
            # 제외 키워드도 수집
            exclusions = DOMAIN_EXCLUSION_KEYWORDS.get(domain, [])
            exclusion_keywords.update(kw.lower() for kw in exclusions)

        if not user_keywords:
            return certificates

        filtered = []
        for cert in certificates:
            career_info = cert.get("career_info") or {}
            job_market = cert.get("job_market_info") or {}

            # 자격증의 텍스트 정보 수집 (확장된 범위)
            cert_text_parts: list[str] = []

            # 1. title 추가 (NEW: 2026-02-06)
            title = cert.get("title", "")
            if title:
                cert_text_parts.append(title)

            # 2. overview 추가 (NEW: 2026-02-06)
            overview = cert.get("overview", "")
            if overview:
                cert_text_parts.append(overview)

            # 3. industry (기존)
            industry = career_info.get("industry", [])
            if isinstance(industry, list):
                cert_text_parts.extend(industry)
            elif industry:
                cert_text_parts.append(str(industry))

            # 4. preferred_industries (기존)
            preferred = job_market.get("preferred_industries", [])
            if preferred:
                cert_text_parts.extend(preferred)

            # 5. related_jobs (NEW: 2026-02-06)
            related_jobs = career_info.get("related_jobs", [])
            if related_jobs:
                cert_text_parts.extend(related_jobs)

            cert_text = " ".join(cert_text_parts).lower()

            # 제외 키워드가 포함되면 스킵
            if any(kw in cert_text for kw in exclusion_keywords):
                continue

            # 사용자 키워드 중 하나라도 매칭되면 포함
            if any(kw in cert_text for kw in user_keywords):
                filtered.append(cert)

        # 2026-02-06 수정: 폴백 제거
        # 매칭 결과 0개면 빈 리스트 반환 (무관 자격증 추천 방지)
        # 기존: if len(filtered) == 0: return certificates
        return filtered

    def _match_domains_to_certificate(
        self, cert: Certificate, request: RecommendationRequest
    ) -> tuple[list[str], float]:
        """사용자 관심 도메인과 자격증 산업 매칭을 수행합니다.

        Args:
            cert: 자격증 객체.
            request: 사용자 추천 요청.

        Returns:
            (매칭된 도메인 리스트, 매칭 비율) 튜플.
        """
        matched_domains: list[str] = []
        career_info = cert.career_info or {}
        job_market = cert.job_market_info or {}

        # 자격증의 산업 정보 수집
        cert_industries: list[str] = []
        if career_info.get("industry"):
            industry = career_info["industry"]
            if isinstance(industry, list):
                cert_industries.extend(industry)
            else:
                cert_industries.append(str(industry))

        if job_market.get("preferred_industries"):
            cert_industries.extend(job_market["preferred_industries"])

        # 산업 텍스트를 소문자로 통합
        cert_industry_text = " ".join(cert_industries).lower()

        # 각 관심 도메인이 자격증 산업과 매칭되는지 확인
        for domain in request.interest_domains:
            keywords = DOMAIN_INDUSTRY_MAPPING.get(domain, [])
            for keyword in keywords:
                if keyword.lower() in cert_industry_text:
                    matched_domains.append(domain)
                    break  # 하나만 매칭되면 충분

        # 매칭 비율 계산
        if request.interest_domains:
            match_ratio = len(matched_domains) / len(request.interest_domains)
        else:
            match_ratio = 0.0

        return matched_domains, match_ratio

    def _build_personalized_intro(
        self, matched_domains: list[str], request: RecommendationRequest
    ) -> str:
        """사용자 맥락 기반 개인화된 첫 문장을 생성합니다.

        패턴: "{도메인} {목적}을 준비하시는 분께 적합합니다."

        Args:
            matched_domains: 매칭된 도메인 리스트.
            request: 사용자 추천 요청.

        Returns:
            개인화된 인트로 문자열.
        """
        if not matched_domains:
            return ""

        # 도메인 텍스트 (최대 2개)
        domain_text = ", ".join(matched_domains[:2])

        # 목적 텍스트 변환
        purpose_text = request.purpose
        if purpose_text == "취업":
            purpose_text = "취업"
        elif purpose_text == "이직":
            purpose_text = "이직"
        elif purpose_text == "자기계발":
            purpose_text = "자기계발"
        elif purpose_text == "업무능력 향상":
            purpose_text = "업무능력 향상"

        return f"{domain_text} 분야 {purpose_text}을 준비하시는 분께 적합합니다."

    def _build_timeline_fit_phrase(
        self, cert: Certificate, request: RecommendationRequest
    ) -> str:
        """준비 기간 적합성 문구를 생성합니다.

        Args:
            cert: 자격증 객체.
            request: 사용자 추천 요청.

        Returns:
            타임라인 적합성 문구.
        """
        if not cert.study_period_days:
            return ""

        timeline_text = TIMELINE_DISPLAY_TEXT.get(request.study_timeline, "")
        if not timeline_text:
            return ""

        available_days = AVAILABLE_DAYS.get(request.study_timeline, 365)
        study_days = cert.study_period_days

        if study_days <= available_days * 0.6:
            return f"{timeline_text} 목표 기간 내 충분히 준비 가능합니다."
        elif study_days <= available_days:
            return f"{timeline_text} 기간 내 준비 가능한 자격증입니다."

        return ""

    def _build_difficulty_fit_phrase(
        self, cert: Certificate, request: RecommendationRequest
    ) -> str:
        """난이도 적합성 문구를 생성합니다.

        Args:
            cert: 자격증 객체.
            request: 사용자 추천 요청.

        Returns:
            난이도 적합성 문구.
        """
        if not cert.difficulty:
            return ""

        max_difficulty = DIFFICULTY_LIMITS.get(request.difficulty_preference)
        if max_difficulty is None:
            return ""

        if cert.difficulty <= max_difficulty:
            if request.difficulty_preference == "쉬운 편":
                return "선호하시는 쉬운 난이도에 맞는 자격증입니다."
            elif request.difficulty_preference == "중간":
                return "중간 난이도로 적당히 도전적인 자격증입니다."

        return ""

    def _generate_reason(
        self, cert: Certificate, request: RecommendationRequest
    ) -> str:
        """자격증 추천 사유를 생성합니다.

        자격증별 고유 특성과 사용자 검색 조건을 반영한 개인화된 추천 사유를 생성합니다.
        첫 문장: purpose(목적) 반영 → 두 번째: 자격증 특성 → 세 번째: 학습 관련

        Args:
            cert: 자격증 객체.
            request: 사용자 추천 요청.

        Returns:
            추천 사유 문자열.
        """
        career_info = cert.career_info or {}
        job_market = cert.job_market_info or {}
        feasibility = cert.feasibility_info or {}

        # 1. 도메인 매칭 수행
        matched_domains, match_ratio = self._match_domains_to_certificate(cert, request)

        result_parts: list[str] = []

        # 2. 첫 문장: purpose(목적) 기반 인트로 (가장 먼저 선택한 조건)
        purpose_intro = self._build_purpose_based_intro(cert, request)
        if purpose_intro:
            result_parts.append(purpose_intro)

        # 3. 두 번째: 메인 이유 생성 (자격증 고유 특성)
        main_reason = self._build_main_reason(
            cert, request, career_info, job_market, matched_domains
        )
        if main_reason and main_reason not in result_parts:
            result_parts.append(main_reason)

        # 4. 세 번째: 학습 관련 문구 (study_commitment)
        if len(result_parts) < 3:
            commitment_phrase = self._build_commitment_based_phrase(cert, request)
            if commitment_phrase:
                result_parts.append(commitment_phrase)
            else:
                # 폴백: 기존 부가 포인트
                supporting_points = self._build_supporting_points(
                    cert, request, career_info, job_market, feasibility
                )
                if supporting_points:
                    result_parts.append(supporting_points[0])

        return " ".join(filter(None, result_parts))

    def _build_main_reason(
        self,
        cert: Certificate,
        request: RecommendationRequest,
        career_info: dict,
        job_market: dict,
        matched_domains: list[str] | None = None,
    ) -> str:
        """핵심 추천 이유를 생성합니다.

        Args:
            cert: 자격증 객체.
            request: 사용자 추천 요청.
            career_info: 자격증 경력 정보.
            job_market: 채용 시장 정보.
            matched_domains: 매칭된 사용자 관심 도메인 리스트.

        Returns:
            핵심 추천 이유 문자열.
        """
        matched_domains = matched_domains or []

        # 1순위: 채용 시장에서의 가치 (매칭된 도메인 우선 활용)
        requirement_type = job_market.get("requirement_type", "")
        job_frequency = job_market.get("job_posting_frequency", "")

        if requirement_type == "필수" or job_frequency in ["매우 높음", "매우 많음"]:
            # 매칭된 도메인이 있으면 우선 사용
            if matched_domains:
                domain_text = ", ".join(matched_domains[:2])
                return f"{domain_text} 분야 채용에서 우대 요건으로 자주 등장하는 자격증입니다."
            industries = job_market.get("preferred_industries", [])[:2]
            if industries:
                return f"{', '.join(industries)} 분야 채용에서 높은 수요를 보이는 자격증입니다."

        # 2순위: 공무원/공기업 가산점
        public_points = job_market.get("public_sector_points", "")
        if public_points and request.purpose in ["취업", "이직"]:
            return f"공무원·공기업 채용 시 {public_points}의 가산점 혜택이 있습니다."

        # 3순위: 관련 직업과 연계
        related_jobs = career_info.get("related_jobs", [])
        use_cases = career_info.get("use_cases", [])

        if related_jobs:
            jobs_text = ", ".join(related_jobs[:3])
            return f"{jobs_text} 직무에서 전문성을 인정받을 수 있는 자격증입니다."

        if use_cases:
            cases_text = ", ".join(use_cases[:2])
            return f"{cases_text} 업무에 실질적으로 활용되는 자격증입니다."

        # 4순위: 산업 분야
        industry = career_info.get("industry", [])
        if industry:
            industry_text = (
                ", ".join(industry[:2]) if isinstance(industry, list) else industry
            )
            return f"{industry_text} 산업에서 경쟁력을 높일 수 있는 자격증입니다."

        # 기본값
        if cert.series:
            return f"{cert.series} 계열의 대표적인 자격증입니다."

        return f"{cert.title}은(는) 해당 분야의 전문성을 증명하는 자격증입니다."

    def _build_supporting_points(
        self,
        cert: Certificate,
        request: RecommendationRequest,
        career_info: dict,
        job_market: dict,
        feasibility: dict,
    ) -> list[str]:
        """부가 추천 포인트를 생성합니다.

        타임라인/난이도 적합성을 우선 반영합니다.
        """
        points = []

        # 0. 타임라인 적합성 (최우선)
        timeline_phrase = self._build_timeline_fit_phrase(cert, request)
        if timeline_phrase:
            points.append(timeline_phrase)

        # 0.5. 난이도 적합성
        difficulty_phrase = self._build_difficulty_fit_phrase(cert, request)
        if difficulty_phrase and len(points) < 2:
            points.append(difficulty_phrase)

        # 1. 비전공자/직장인 친화도
        self_study = feasibility.get("self_study_possible")
        non_major_rate = feasibility.get("non_major_pass_rate", "")
        working_tips = feasibility.get("working_adult_tips", [])

        if len(points) < 2 and self_study and non_major_rate:
            points.append(
                f"비전공자도 독학으로 도전 가능하며 합격률은 {non_major_rate}입니다."
            )
        elif len(points) < 2 and self_study:
            points.append("독학으로 충분히 합격 가능한 자격증입니다.")

        if working_tips and len(points) < 2:
            points.append("직장인도 출퇴근 시간을 활용해 준비할 수 있습니다.")

        # 2. 연봉/급여 효과
        salary_premium = job_market.get("salary_premium", "")
        avg_salary = career_info.get("average_salary", "")

        if salary_premium and len(points) < 2:
            points.append(
                f"취득 시 {salary_premium}의 연봉 상승 효과를 기대할 수 있습니다."
            )
        elif avg_salary and len(points) < 2:
            points.append(f"관련 직종 평균 연봉은 {avg_salary}입니다.")

        # 3. 준비 기간 상세 (타임라인 문구가 없을 때만)
        if (
            not timeline_phrase
            and cert.study_period_days
            and request.study_timeline
            and len(points) < 2
        ):
            available_days = AVAILABLE_DAYS.get(request.study_timeline, 365)
            study_days = cert.study_period_days
            months = max(1, study_days // 30)

            if study_days <= available_days * 0.5:
                points.append(
                    f"약 {months}개월 준비로 여유 있게 합격을 노릴 수 있습니다."
                )
            elif study_days <= available_days:
                points.append(f"약 {months}개월 준비 기간이 필요합니다.")

        # 4. 취업 전망 (문장 단위로 자르기)
        job_prospects = career_info.get("job_prospects", "")
        if job_prospects and len(points) < 2:
            # 첫 번째 문장만 추출
            first_sentence = self._extract_first_sentence(job_prospects)
            if first_sentence:
                points.append(first_sentence)

        return points

    def _extract_first_sentence(self, text: str) -> str:
        """텍스트에서 첫 번째 문장을 추출합니다."""
        if not text:
            return ""

        # 문장 구분자로 분리
        for delimiter in [".", "합니다.", "입니다.", "있습니다."]:
            if delimiter in text:
                idx = text.find(delimiter)
                sentence = text[: idx + len(delimiter)].strip()
                # 너무 짧거나 긴 경우 제외
                if 10 <= len(sentence) <= 80:
                    return sentence

        # 구분자가 없으면 80자 이내로 자르되, 단어 단위로
        if len(text) <= 80:
            return text

        truncated = text[:80]
        last_space = truncated.rfind(" ")
        if last_space > 40:
            return truncated[:last_space].strip()

        return ""

    def _generate_key_points(
        self, cert: Certificate, request: RecommendationRequest
    ) -> list[str]:
        """자격증 추천 핵심 포인트를 생성합니다.

        난이도, 학습 팁, 준비 기간, 관련 직업/활용 분야 위주로
        핵심 포인트를 제공합니다.

        Args:
            cert: 자격증 객체.
            request: 사용자 추천 요청.

        Returns:
            핵심 포인트 목록(최대 5개).
        """
        points: list[str] = []

        # 1. 난이도 문구
        if cert.difficulty:
            difficulty_labels = {
                1: "초급 난이도로 입문자에게 적합",
                2: "중하 난이도로 기초 지식으로 도전 가능",
                3: "중급 난이도로 체계적 학습 필요",
                4: "중상 난이도로 전문 학습 필요",
                5: "고급 난이도로 장기 준비 필요",
            }
            label = difficulty_labels.get(cert.difficulty, "")
            if label:
                points.append(f"난이도: {label}")

        # 2. 학습 팁 (user_reviews.study_tips에서 첫 번째)
        user_reviews = cert.user_reviews or {}
        study_tips = user_reviews.get("study_tips", [])
        if study_tips and len(study_tips) > 0:
            tip = study_tips[0]
            # 팁이 너무 길면 줄임 (100자 제한)
            if len(tip) > 100:
                tip = tip[:100] + "..."
            points.append(f"학습 팁: {tip}")

        # 3. 준비 기간
        if cert.study_period_days:
            days = cert.study_period_days
            if days <= 30:
                points.append("약 1개월 준비 기간")
            elif days <= 60:
                points.append("약 1-2개월 준비 기간")
            elif days <= 90:
                points.append("약 3개월 준비 기간")
            elif days <= 180:
                points.append("약 6개월 준비 기간")
            else:
                months = days // 30
                points.append(f"약 {months}개월 준비 기간")

        # 4. 관련 직업
        career_info = cert.career_info or {}
        if career_info.get("related_jobs"):
            jobs = career_info["related_jobs"][:2]
            points.append(f"관련 직업: {', '.join(jobs)}")

        # 5. 활용 분야
        if len(points) < 5 and career_info.get("use_cases"):
            use_cases = career_info["use_cases"][:2]
            points.append(f"활용 분야: {', '.join(use_cases)}")

        # 기본값
        if not points:
            points.append(f"{request.purpose} 목표에 도움이 되는 선택")

        return points[:5]  # 최대 5개

    def _calculate_feasibility(
        self, cert: Certificate, request: RecommendationRequest
    ) -> Feasibility:
        """자격증 준비 가능성을 계산합니다.

        Args:
            cert: 자격증 객체.
            request: 사용자 추천 요청.

        Returns:
            Feasibility 객체.
        """
        # Get study period (default to 90 days if not available)
        study_days = cert.study_period_days or 90

        # Calculate available days based on timeline
        available_days = AVAILABLE_DAYS.get(request.study_timeline, 365)

        # User can prepare if study_days <= available_days
        can_prepare = study_days <= available_days

        return Feasibility(
            can_prepare=can_prepare,
            estimated_days=study_days,
        )

    def _build_quick_stats(self, cert: Certificate) -> QuickStats:
        """MariaDB 데이터에서 QuickStats를 생성합니다.

        Args:
            cert: 자격증 객체.

        Returns:
            QuickStats 객체.
        """
        # 합격률
        passing_rate = cert.passing_rate

        # 평균 연봉 (career_info에서)
        career_info = cert.career_info or {}
        average_salary = career_info.get("average_salary")

        # 응시료 (exam_info에서)
        exam_info = cert.exam_info or {}
        exam_fee = exam_info.get("total_fee")

        # 시험 유형 (exam_info에서)
        exam_type = exam_info.get("exam_type")

        return QuickStats(
            passing_rate=passing_rate,
            average_salary=average_salary,
            exam_fee=exam_fee,
            exam_type=exam_type,
        )

    def _build_study_insights(self, cert: Certificate) -> StudyInsights:
        """MariaDB 데이터에서 StudyInsights를 생성합니다.

        Args:
            cert: 자격증 객체.

        Returns:
            StudyInsights 객체.
        """
        # 학습 팁 (user_reviews에서, 최대 3개)
        user_reviews = cert.user_reviews or {}
        study_tips = user_reviews.get("study_tips", [])[:3]

        # 합격 팁 (study_guide에서, 최대 2개)
        study_guide = cert.study_guide or {}
        success_tips = study_guide.get("success_tips", [])[:2]

        # 난이도 피드백 (user_reviews에서)
        difficulty_feedback = user_reviews.get("difficulty_feedback")

        return StudyInsights(
            study_tips=study_tips,
            success_tips=success_tips,
            difficulty_feedback=difficulty_feedback,
        )

    def _generate_query_summary(self, request: RecommendationRequest) -> str:
        """사용자 질의 요약을 생성합니다.

        Args:
            request: 사용자 추천 요청.

        Returns:
            질의 요약 문자열.
        """
        domains = ", ".join(request.interest_domains)
        parts = [
            f"{request.purpose} 목적",
            f"관심 분야: {domains}",
            f"준비 기간: {request.study_timeline}",
            f"난이도 선호: {request.difficulty_preference}",
        ]

        return " | ".join(parts)

    # ===== RAG-Specific Methods =====

    def _build_query_text(self, request: RecommendationRequest) -> str:
        """사용자 요청을 벡터 검색용 쿼리 텍스트로 변환합니다.

        자격증 임베딩 형식과 유사하게 구조화하여 벡터 유사도를 높입니다.
        새 필드(target_jobs, target_industries, certificate_level, specific_keywords)를
        활용하여 더 정확한 검색을 수행합니다.

        Args:
            request: 사용자 추천 요청.

        Returns:
            임베딩 생성용 쿼리 텍스트.
        """
        parts = []

        # 1. 특정 키워드 (가장 높은 우선순위)
        specific_keywords = getattr(request, "specific_keywords", None)
        if specific_keywords:
            keywords_text = ", ".join(specific_keywords)
            parts.append(f"[핵심 키워드] {keywords_text}")

        # 2. 자격증 등급 (계열)
        certificate_level = getattr(request, "certificate_level", None)
        if certificate_level and certificate_level != "상관없음":
            parts.append(f"계열: {certificate_level}")

        # 3. 산업 분야 (자격증 임베딩 형식과 유사하게)
        target_industries = getattr(request, "target_industries", None)
        if target_industries:
            industries_text = ", ".join(target_industries)
            parts.append(f"산업분야: {industries_text}")

        # 4. 관련 직업 (자격증 임베딩 형식과 유사하게)
        target_jobs = getattr(request, "target_jobs", None)
        if target_jobs:
            jobs_text = ", ".join(target_jobs)
            parts.append(f"관련직업: {jobs_text}")

        # 5. user_summary (사용자 자유 입력)
        user_summary = (request.user_summary or "").strip()
        if user_summary:
            parts.append(f"[사용자 요청] {user_summary}")

        # 6. 관심 분야 (interest_domains)
        domain_text = ", ".join(request.interest_domains)
        parts.append(f"분야: {domain_text}")

        # 6.5. 산업 키워드 강화 (2026-02-06)
        # interest_domains에 매핑된 산업 키워드를 추가하여 벡터 검색 품질 향상
        industry_keywords: list[str] = []
        for domain in request.interest_domains:
            keywords = DOMAIN_INDUSTRY_MAPPING.get(domain, [])
            industry_keywords.extend(keywords[:3])  # 분야당 최대 3개

        if industry_keywords:
            parts.append(f"산업키워드: {', '.join(industry_keywords)}")

        # 7. 기본 조건
        timeline = request.study_timeline
        difficulty = request.difficulty_preference
        parts.append(f"목적: {request.purpose}")
        parts.append(f"난이도: {difficulty}")
        parts.append(f"준비기간: {timeline}")

        # 새 필드가 있으면 구조화된 형식 사용
        if specific_keywords or certificate_level or target_industries or target_jobs:
            return "\n".join(parts)

        # user_summary가 있으면 3중 강조 (기존 로직 유지)
        if user_summary:
            industry_hint = ""
            if industry_keywords:
                industry_hint = f"\n산업키워드: {', '.join(industry_keywords)}"
            return (
                f"[최우선 요청] {user_summary}\n\n"
                f"배경: {request.purpose}, {domain_text} 분야, "
                f"기간 {timeline}, 난이도 {difficulty}{industry_hint}\n\n"
                f"[핵심 키워드] {user_summary}\n\n"
                f"[사용자 요청] {user_summary}"
            )

        # 새 필드도 user_summary도 없으면 기존 로직 + 산업 키워드 강화
        industry_hint = ""
        if industry_keywords:
            industry_hint = f"\n산업분야 키워드: {', '.join(industry_keywords)}"

        intent_sentence = (
            f"{request.purpose} 목적의 사용자가 {domain_text} 분야와 연관된 자격증을 찾고 있습니다. "
            f"career_info의 industry/use_cases/related_jobs가 유사한 자격증을 우선 고려해주세요.{industry_hint}"
        )
        constraint_sentence = (
            f"예상 공부 기간은 {timeline}이며, 선호 난이도는 {difficulty}입니다."
        )

        return f"{intent_sentence}\n\n{constraint_sentence}"

    def _calculate_keyword_matching_bonus(
        self, cert: Certificate, request: RecommendationRequest
    ) -> int:
        """새 필드 키워드와 자격증 데이터 매칭 보너스를 계산합니다.

        target_jobs, target_industries, certificate_level, specific_keywords가
        자격증 데이터와 매칭될 때 보너스 점수를 부여합니다.

        Args:
            cert: 자격증 객체.
            request: 사용자 추천 요청.

        Returns:
            보너스 점수 (0-25).
        """
        bonus = 0
        career_info = cert.career_info or {}
        job_market = cert.job_market_info or {}

        # 1. specific_keywords 매칭 (+5점: 제목, +3점: 개요/산업)
        specific_keywords = getattr(request, "specific_keywords", None)
        if specific_keywords:
            title_lower = cert.title.lower()
            overview_lower = (cert.overview or "").lower()

            # 산업 분야 텍스트
            industry = career_info.get("industry", [])
            if isinstance(industry, list):
                industry_text = " ".join(industry).lower()
            else:
                industry_text = str(industry).lower()

            for keyword in specific_keywords:
                kw_lower = keyword.lower()
                if kw_lower in title_lower:
                    bonus += 5  # 제목 매칭
                elif kw_lower in overview_lower or kw_lower in industry_text:
                    bonus += 3  # 개요/산업 매칭

        # 2. certificate_level 매칭 (+10점: 정확히 일치)
        certificate_level = getattr(request, "certificate_level", None)
        if certificate_level and certificate_level != "상관없음":
            series = cert.series or ""
            if certificate_level in series:
                bonus += 10

        # 3. target_jobs 매칭 (+5점: 관련 직업에 포함)
        target_jobs = getattr(request, "target_jobs", None)
        if target_jobs:
            related_jobs = career_info.get("related_jobs", [])
            related_jobs_text = " ".join(related_jobs).lower()
            for job in target_jobs:
                if job.lower() in related_jobs_text:
                    bonus += 5
                    break  # 최대 1회

        # 4. target_industries 매칭 (+3점: 산업 분야에 포함)
        target_industries = getattr(request, "target_industries", None)
        if target_industries:
            # career_info의 industry
            industry = career_info.get("industry", [])
            if isinstance(industry, list):
                industry_text = " ".join(industry).lower()
            else:
                industry_text = str(industry).lower()

            # job_market_info의 preferred_industries
            preferred = job_market.get("preferred_industries", [])
            preferred_text = " ".join(preferred).lower() if preferred else ""

            combined_text = f"{industry_text} {preferred_text}"

            for ind in target_industries:
                if ind.lower() in combined_text:
                    bonus += 3
                    break  # 최대 1회

        # 최대 25점으로 제한
        return min(bonus, 25)

    def _calculate_user_summary_bonus(
        self, cert: Certificate, user_summary: str | None
    ) -> int:
        """user_summary 키워드와 자격증 데이터 매칭 보너스를 계산합니다.

        사용자가 입력한 요청 문장의 키워드가 자격증 제목, 관련 직업,
        활용 분야에 포함되어 있으면 보너스 점수를 부여합니다.

        Args:
            cert: 자격증 객체.
            user_summary: 사용자가 입력한 원본 요청 문장.

        Returns:
            보너스 점수 (0-10).
        """
        if not user_summary:
            return 0

        bonus = 0
        # 2글자 이상인 키워드만 추출 (불용어 제거)
        keywords = {w.lower() for w in user_summary.split() if len(w) > 1}

        if not keywords:
            return 0

        # 제목 매칭: +5점
        title = cert.title.lower()
        if any(kw in title for kw in keywords):
            bonus += 5

        # 관련 직업/활용 분야 매칭: +3점씩
        career_info = cert.career_info or {}
        related_jobs = career_info.get("related_jobs", [])
        use_cases = career_info.get("use_cases", [])

        jobs_text = " ".join(related_jobs).lower()
        cases_text = " ".join(use_cases).lower()

        if any(kw in jobs_text for kw in keywords):
            bonus += 3

        if any(kw in cases_text for kw in keywords):
            bonus += 3

        return min(bonus, 10)  # 최대 10점

    def _build_vector_filter(self, request: RecommendationRequest) -> Optional[dict]:
        """벡터 검색용 ChromaDB where 필터를 생성합니다.

        B6 수정: 메타데이터 필터를 활용하여 벡터 검색 성능 향상.
        """
        constraints = self._build_constraints(request)
        filters = []

        # 난이도 필터
        max_difficulty = constraints.get("max_difficulty")
        if max_difficulty is not None:
            filters.append({"difficulty": {"$lte": max_difficulty}})

        # 학습 기간 필터
        max_study_days = constraints.get("max_study_days")
        if max_study_days is not None:
            filters.append({"study_period_days": {"$lte": max_study_days}})

        if not filters:
            return None

        if len(filters) == 1:
            return filters[0]

        return {"$and": filters}

    def _fetch_certificates_by_ids(self, cert_ids: list[str]) -> list[dict[str, Any]]:
        """ID 리스트로 자격증 전체 데이터를 조회합니다.

        SQLAlchemy를 사용하여 MariaDB에서 동기적으로 조회합니다.
        (B1 수정: async → sync 변환하여 이벤트 루프 블로킹 방지)

        Args:
            cert_ids: 조회할 자격증 ID 리스트.

        Returns:
            자격증 딕셔너리 목록.
        """
        if not cert_ids:
            return []

        results = (
            self.db.query(CertificateModel)
            .filter(CertificateModel.id.in_(cert_ids))
            .all()
        )

        return [cert.to_dict() for cert in results]

    def _generate_recommendations_from_vector_results(
        self,
        similar_results: list[dict],
        certificates: list[dict[str, Any]],
        request: RecommendationRequest,
        constraints: Optional[dict[str, Any]] = None,
    ) -> list[RecommendedCertificate]:
        """벡터 검색 결과를 RecommendedCertificate 객체로 변환합니다.

        Args:
            similar_results: ChromaDB 벡터 검색 결과.
            certificates: MariaDB에서 조회한 전체 자격증 데이터.
            request: 사용자 추천 요청.
            constraints: 하드 필터 정보.

        Returns:
            RecommendedCertificate 객체 목록.
        """
        # Create cert ID to full data mapping
        cert_map = {cert["id"]: cert for cert in certificates}

        # Create cert ID to similarity score mapping
        score_map = {result["id"]: result["score"] for result in similar_results}

        recommendations = []

        for cert_id in cert_map:
            cert_data = cert_map[cert_id]
            similarity_score = score_map.get(cert_id, 0.0)

            # Parse certificate early for constraint checks
            cert = Certificate(**cert_data)

            # Convert similarity score (0.0-1.0) to match_score (0-100)
            match_score = int(similarity_score * 100)

            if constraints:
                max_diff = constraints.get("max_difficulty")
                max_days = constraints.get("max_study_days")
                if (
                    max_diff is not None
                    and cert.difficulty
                    and cert.difficulty <= max_diff
                ):
                    match_score = min(100, match_score + 5)
                if (
                    max_days is not None
                    and cert.study_period_days
                    and cert.study_period_days <= max_days
                ):
                    match_score = min(100, match_score + 5)

            # user_summary 키워드 매칭 보너스 적용
            user_bonus = self._calculate_user_summary_bonus(cert, request.user_summary)
            match_score = min(100, match_score + user_bonus)

            # 새 필드 키워드 매칭 보너스 적용
            keyword_bonus = self._calculate_keyword_matching_bonus(cert, request)
            match_score = min(100, match_score + keyword_bonus)

            # Generate recommendation reason
            reason = self._generate_reason(cert, request)

            # Generate key points
            key_points = self._generate_key_points(cert, request)

            # Calculate feasibility
            feasibility = self._calculate_feasibility(cert, request)

            # Build quick stats and study insights
            quick_stats = self._build_quick_stats(cert)
            study_insights = self._build_study_insights(cert)

            # Get primary category name from categories array
            primary_category = cert.categories[0].name if cert.categories else "기타"

            recommendations.append(
                RecommendedCertificate(
                    certificate=cert,
                    qualification_category=primary_category,
                    match_score=match_score,
                    recommendation_reason=reason,
                    key_points=key_points,
                    feasibility=feasibility,
                    quick_stats=quick_stats,
                    study_insights=study_insights,
                )
            )

        # Sort by match_score descending
        recommendations.sort(key=lambda x: x.match_score, reverse=True)

        return recommendations

    # ===== Soft Filter Methods (신규) =====

    def _calculate_status_bonus(
        self, cert: Certificate, request: RecommendationRequest
    ) -> int:
        """현재 상황(current_status)에 따른 점수 보너스를 계산합니다.

        Args:
            cert: 자격증 객체.
            request: 사용자 추천 요청.

        Returns:
            보너스 점수 (0-10).
        """
        status = getattr(request, "current_status", None)
        if not status or not cert.difficulty:
            return 0

        difficulty_range = STATUS_DIFFICULTY_MAPPING.get(status)
        if not difficulty_range:
            return 0

        min_diff, max_diff = difficulty_range

        # 적합 난이도 범위 내에 있으면 보너스
        if min_diff <= cert.difficulty <= max_diff:
            # 범위 중앙에 가까울수록 높은 보너스 (최소 5점 보장)
            center = (min_diff + max_diff) / 2
            distance = abs(cert.difficulty - center)
            max_distance = (max_diff - min_diff) / 2
            if max_distance > 0:
                # 최소 5점, 최대 10점
                return max(5, int(10 * (1 - distance / max_distance)))
            return 10

        return 0

    def _calculate_commitment_bonus(
        self, cert: Certificate, request: RecommendationRequest
    ) -> int:
        """투자 시간(study_commitment)에 따른 점수 보너스를 계산합니다.

        Args:
            cert: 자격증 객체.
            request: 사용자 추천 요청.

        Returns:
            보너스 점수 (0-8).
        """
        commitment = getattr(request, "study_commitment", None)
        if not commitment:
            return 0

        # unsure는 항상 기본 보너스
        if commitment == "unsure":
            return 4

        study_days = cert.study_period_days or 90
        days_range = COMMITMENT_DAYS_MAPPING.get(commitment)
        if not days_range:
            return 0

        min_days, max_days = days_range

        # 적합 기간 범위 내에 있으면 보너스
        if min_days <= study_days <= max_days:
            # 짧을수록 높은 보너스 (relaxed, moderate에 유리)
            if commitment == "relaxed":
                # 짧을수록 높은 점수
                if study_days <= 30:
                    return 8
                elif study_days <= 60:
                    return 6
                else:
                    return 4
            elif commitment == "moderate":
                if study_days <= 90:
                    return 8
                elif study_days <= 120:
                    return 6
                else:
                    return 4
            elif commitment == "intensive":
                # intensive는 기간 상관없이 높은 보너스
                return 8

        return 2  # 범위 밖이어도 최소 보너스

    def _apply_soft_constraints(
        self,
        certificates: list[dict[str, Any]],
        constraints: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """소프트 필터를 적용하여 점수 보너스를 부여합니다.

        하드 필터와 달리 필터링하지 않고, 조건 충족 시 보너스만 부여합니다.

        Args:
            certificates: 자격증 딕셔너리 목록.
            constraints: 제약조건 딕셔너리.

        Returns:
            soft_bonus가 추가된 자격증 딕셔너리 목록.
        """
        max_days = constraints.get("max_study_days")
        max_difficulty = constraints.get("max_difficulty")

        result = []
        for cert in certificates:
            soft_bonus = 0

            # 타임라인 매칭 보너스 (+5%)
            study_days = cert.get("study_period_days")
            if max_days is not None and study_days:
                if study_days <= max_days:
                    soft_bonus += 5

            # 난이도 매칭 보너스 (+5%)
            difficulty = cert.get("difficulty")
            if max_difficulty is not None and difficulty:
                if difficulty <= max_difficulty:
                    soft_bonus += 5

            cert_copy = dict(cert)
            cert_copy["soft_bonus"] = soft_bonus
            result.append(cert_copy)

        return result

    def _apply_fallback_if_empty(
        self,
        filtered_results: list[dict],
        all_results: list[dict],
        certificates: list[dict[str, Any]],
        fallback_count: int = FALLBACK_COUNT,
    ) -> list[dict]:
        """필터링 결과가 비어있을 때 폴백 결과를 반환합니다.

        Args:
            filtered_results: 필터링된 결과 목록.
            all_results: 전체 벡터 검색 결과 목록.
            certificates: 자격증 딕셔너리 목록.
            fallback_count: 폴백 시 반환할 결과 수.

        Returns:
            결과 목록 (필터 결과가 있으면 그대로, 없으면 폴백).
        """
        if filtered_results:
            return filtered_results

        # 폴백: 유사도 상위 N개 반환
        sorted_results = sorted(all_results, key=lambda x: x["score"], reverse=True)
        return sorted_results[:fallback_count]

    # ===== 개인화 추천 이유 메서드 (NEW) =====

    def _select_template(self, templates: list[str], cert_id: str, seed: str) -> str:
        """결정적 템플릿 선택 (동일 입력 = 동일 출력).

        자격증 ID와 seed를 해시하여 일관된 인덱스를 선택합니다.
        """
        if not templates:
            return ""
        hash_input = f"{cert_id}_{seed}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        return templates[hash_value % len(templates)]

    def _build_purpose_based_intro(
        self, cert: Certificate, request: RecommendationRequest
    ) -> str:
        """purpose(목적) 기반 첫 문장을 생성합니다.

        사용자가 가장 먼저 선택한 조건(목적)을 반영합니다.

        Args:
            cert: 자격증 객체.
            request: 사용자 추천 요청.

        Returns:
            목적 기반 인트로 문자열.
        """
        purpose = request.purpose
        if not purpose:
            return ""

        cert_id = cert.id or "default"
        career_info = cert.career_info or {}
        related_jobs = career_info.get("related_jobs", [])
        job_text = related_jobs[0] if related_jobs else ""

        # 목적별 템플릿
        templates: dict[str, list[str]] = {
            "취업": [
                "취업 준비에 강점이 되는 자격증입니다.",
                "채용 시장에서 경쟁력을 높여줄 자격증입니다.",
                "취업에 유리한 실용적인 자격증입니다.",
                "입사 지원 시 어필할 수 있는 자격증입니다.",
                "취업 준비생에게 추천하는 자격증입니다.",
            ],
            "이직": [
                "이직 준비에 도움이 되는 자격증입니다.",
                "커리어 전환이나 연봉 협상에 유리합니다.",
                "경력 개발에 플러스가 되는 자격증입니다.",
                "이직 시장에서 가치를 인정받는 자격증입니다.",
                "새로운 기회를 위한 발판이 됩니다.",
            ],
            "커리어 전문성 강화": [
                "전문성을 한 단계 높여줄 자격증입니다.",
                "해당 분야 전문가로 인정받을 수 있습니다.",
                "깊이 있는 역량을 증명할 수 있는 자격증입니다.",
                "커리어 성장에 도움이 되는 자격증입니다.",
                "전문가로서의 입지를 다지는 데 적합합니다.",
            ],
            "창업 / 실무 활용": [
                "실무에서 바로 활용할 수 있는 자격증입니다.",
                "창업이나 사업 운영에 도움이 됩니다.",
                "실용적인 지식을 얻을 수 있는 자격증입니다.",
                "현장에서 인정받는 실무 자격증입니다.",
                "비즈니스에 직접 적용 가능한 내용을 다룹니다.",
            ],
            "개인 관심 / 교양": [
                "관심 분야를 체계적으로 배울 수 있는 자격증입니다.",
                "교양과 자기계발에 적합한 자격증입니다.",
                "흥미로운 분야를 깊이 탐구할 수 있습니다.",
                "취미와 실력을 동시에 키울 수 있습니다.",
                "새로운 분야에 도전하기 좋은 자격증입니다.",
            ],
        }

        # 사용자가 선택한 관심 분야가 있으면 특화된 멘트
        interest_domains = getattr(request, "interest_domains", None) or []
        domain = interest_domains[0] if interest_domains else None

        if domain and purpose in ["취업", "이직"]:
            domain_templates = [
                f"{domain} 분야 {purpose}에 유리한 자격증입니다.",
                f"{domain} 분야 {purpose} 준비에 도움이 되는 자격증입니다.",
                f"{domain} 직무 {purpose}에서 경쟁력을 높여줍니다.",
            ]
            return self._select_template(
                domain_templates, cert_id, f"purpose_domain_{purpose}"
            )

        # 직업 정보가 있으면 특화된 멘트 (모든 템플릿에 purpose 키워드 포함)
        if job_text and purpose in ["취업", "이직"]:
            job_templates = [
                f"{job_text} 분야 {purpose}에 유리한 자격증입니다.",
                f"{job_text} 직무 {purpose} 준비에 도움이 되는 자격증입니다.",
            ]
            return self._select_template(
                job_templates, cert_id, f"purpose_job_{purpose}"
            )

        return self._select_template(
            templates.get(purpose, []), cert_id, f"purpose_{purpose}"
        )

    def _build_status_based_intro(
        self, cert: Certificate, request: RecommendationRequest
    ) -> str:
        """current_status 기반 개인화된 인트로 문구를 생성합니다.

        Args:
            cert: 자격증 객체.
            request: 사용자 추천 요청.

        Returns:
            상황 기반 인트로 문자열.
        """
        status = getattr(request, "current_status", None)
        if not status:
            return ""

        difficulty = cert.difficulty or 3
        career_info = cert.career_info or {}
        related_jobs = career_info.get("related_jobs", [])
        job_text = related_jobs[0] if related_jobs else ""

        # 상황별 인트로 템플릿 (결정적 선택)
        templates: dict[str, list[str]] = {
            "student": [
                "취업 준비에 유리한 자격증입니다.",
                "신입 지원 시 경쟁력을 높여줄 자격증입니다.",
                "입문자도 도전 가능한 자격증으로, 취업 준비에 도움이 됩니다.",
                "첫 자격증으로 추천드립니다. 취업 시장에서 인정받는 자격입니다.",
                "취준생에게 인기 있는 자격증입니다.",
            ],
            "entry_jobseeker": [
                "신입 채용에서 우대받는 자격증입니다.",
                "첫 직장을 찾는 분께 추천드립니다.",
                "입사 지원 시 가산점을 받을 수 있는 자격증입니다.",
                "신입으로 시작하기 좋은 기본기를 다질 수 있습니다.",
                "채용 공고에서 자주 보이는 우대 자격증입니다.",
            ],
            "junior_worker": [
                "1-3년차 경력 개발에 도움이 되는 자격증입니다.",
                "이직 준비나 연봉 협상에 유리한 자격증입니다.",
                "실무 경험과 함께 전문성을 증명할 수 있습니다.",
                "경력 초기에 취득하면 커리어 성장에 도움됩니다.",
                "현직에서 바로 활용 가능한 실용적인 자격증입니다.",
            ],
            "senior_worker": [
                "경력자의 전문성 심화에 적합한 자격증입니다.",
                "리더십 역할이나 커리어 전환을 준비하는 분께 추천드립니다.",
                "고급 역량을 증명할 수 있는 자격증입니다.",
                "4년차 이상 경력자에게 적합한 심화 자격입니다.",
                "전문가로서의 입지를 다지는 데 도움이 됩니다.",
            ],
            "career_break": [
                "재취업 시 경쟁력을 높여줄 자격증입니다.",
                "새로운 시작을 위한 발판이 될 수 있습니다.",
                "경력 단절 후 복귀에 도움이 되는 자격증입니다.",
                "재시작하는 분께 추천드리는 실용적인 자격증입니다.",
                "휴직 중 준비하기 좋은 자격증입니다.",
            ],
        }

        cert_id = cert.id or "default"

        # 난이도에 따른 추가 조건
        if status in ["student", "entry_jobseeker", "career_break"] and difficulty >= 4:
            hard_templates = [
                "도전적인 자격증이지만, 취득 시 큰 경쟁력이 됩니다.",
                "난이도가 있지만, 합격하면 확실한 차별화가 가능합니다.",
            ]
            return self._select_template(hard_templates, cert_id, "hard")

        if status in ["senior_worker"] and difficulty <= 2:
            easy_templates = [
                "빠르게 취득하여 포트폴리오를 보강할 수 있습니다.",
                "단기간에 취득 가능한 실용적인 자격증입니다.",
            ]
            return self._select_template(easy_templates, cert_id, "easy")

        # 직업 정보가 있으면 포함
        if job_text and status in ["junior_worker", "senior_worker"]:
            job_templates = [
                f"{job_text} 직무에서 전문성을 인정받을 수 있는 자격증입니다.",
                f"{job_text} 커리어에 도움이 되는 자격증입니다.",
            ]
            return self._select_template(job_templates, cert_id, "job")

        return self._select_template(templates.get(status, []), cert_id, status)

    def _build_commitment_based_phrase(
        self, cert: Certificate, request: RecommendationRequest
    ) -> str:
        """study_commitment 기반 학습 관련 문구를 생성합니다.

        Args:
            cert: 자격증 객체.
            request: 사용자 추천 요청.

        Returns:
            투자 시간 기반 문구.
        """
        commitment = getattr(request, "study_commitment", None)
        if not commitment:
            return ""

        study_days = cert.study_period_days or 90
        months = max(1, study_days // 30)
        cert_id = cert.id or "default"

        templates: dict[str, list[str]] = {
            "relaxed": [
                f"일상과 병행하며 {months}개월 정도면 충분히 준비 가능합니다.",
                "틈틈이 공부하며 여유 있게 준비할 수 있습니다.",
                "부담 없이 천천히 준비하기 좋은 자격증입니다.",
                "출퇴근 시간을 활용해 병행 가능한 난이도입니다.",
                "주말 학습만으로도 도전 가능합니다.",
            ],
            "moderate": [
                f"주 10시간 정도 투자하면 {months}개월 내 취득 가능합니다.",
                "적당한 학습량으로 균형 있게 준비할 수 있습니다.",
                "무리하지 않으면서 효율적으로 준비 가능합니다.",
                f"기출문제 중심 학습으로 {months}개월 내 합격 가능합니다.",
                "실기와 필기를 병행하며 준비하기 좋습니다.",
            ],
            "intensive": [
                f"집중 학습 시 {max(1, months - 1)}~{months}개월 내 빠른 취득이 가능합니다.",
                "단기 집중으로 효율적인 합격이 가능합니다.",
                "몰입 학습에 적합한 커리큘럼이 있습니다.",
                "전업으로 준비 시 빠르게 취득할 수 있습니다.",
                "집중력을 발휘하면 목표 기간 내 충분히 가능합니다.",
            ],
            "unsure": [
                f"평균 {months}개월 준비로 취득하는 자격증입니다.",
                "학습량을 조절하며 진행할 수 있는 자격증입니다.",
                "상황에 맞게 일정을 조정하며 준비 가능합니다.",
                f"초보자도 {months}개월 내 도전 가능합니다.",
                "온라인 강의와 기출문제로 독학 가능합니다.",
            ],
        }

        # 투자 시간과 준비 기간 매칭 확인
        if commitment == "relaxed" and study_days > 90:
            long_templates = [
                f"여유 있게 준비하면 약 {months}개월 정도 소요됩니다.",
                "천천히 꾸준히 준비하는 것을 추천드립니다.",
            ]
            return self._select_template(long_templates, cert_id, "relaxed_long")

        if commitment == "intensive" and study_days <= 60:
            short_templates = [
                f"집중하면 {months}개월 내 빠르게 취득 가능합니다!",
                "단기 목표로 최적의 자격증입니다.",
            ]
            return self._select_template(short_templates, cert_id, "intensive_short")

        return self._select_template(templates.get(commitment, []), cert_id, commitment)
