"""통합 추천용 키워드 기반 컨텍스트 파서.

LLM 호출 없이 user_input + domains에서 StructuredUserContext를 생성합니다.
통합 추천(/unified) 엔드포인트의 Step 1을 대체하여 ~29초 → ~0초로 개선합니다.
"""

import logging
import re

from app.schemas.recommendation import StructuredUserContext

logger = logging.getLogger(__name__)

# 도메인 → preferred_industries 매핑
_DOMAIN_TO_INDUSTRIES: dict[str, list[str]] = {
    "IT/소프트웨어": ["IT", "소프트웨어"],
    "전기/전자": ["전기", "전자"],
    "건설/건축": ["건설", "건축"],
    "기계/금속": ["기계", "제조"],
    "화학/환경": ["화학", "환경"],
    "금융/회계": ["금융", "회계"],
    "의료/보건": ["의료", "보건"],
    "안전/방재": ["안전", "방재"],
    "식품/농업": ["식품", "농업"],
    "디자인/미디어": ["디자인", "미디어"],
    "경영/사무": ["경영", "사무"],
}


def parse_user_context(
    user_input: str,
    domains: list[str],
) -> StructuredUserContext:
    """user_input과 선택 도메인에서 StructuredUserContext를 생성합니다.

    LLM 호출 없이 키워드 매칭으로 빠르게 파싱합니다.

    Args:
        user_input: 사용자 자연어 입력.
        domains: 선택한 도메인 리스트.

    Returns:
        StructuredUserContext: 파싱된 사용자 상황.
    """
    text = user_input.strip()

    goal = _extract_goal(text)
    employment_status = _extract_employment_status(text)
    major_background = _extract_major_background(text)
    weekly_study_hours = _extract_weekly_hours(text, employment_status)
    max_study_period_days = _extract_study_period(text)
    difficulty_preference = _extract_difficulty(text)
    preferred_industries = _extract_industries(domains)

    ctx = StructuredUserContext(
        goal=goal,
        employment_status=employment_status,
        major_background=major_background,
        weekly_study_hours=weekly_study_hours,
        max_study_period_days=max_study_period_days,
        difficulty_preference=difficulty_preference,
        preferred_industries=preferred_industries,
    )

    logger.info(
        f"[ContextParser] Parsed: goal={goal}, status={employment_status}, "
        f"background={major_background}, period={max_study_period_days}d, "
        f"difficulty={difficulty_preference}"
    )

    return ctx


def build_search_query(
    user_input: str,
    domains: list[str],
) -> str:
    """domains + user_input에서 벡터 검색 쿼리를 생성합니다.

    Args:
        user_input: 사용자 자연어 입력.
        domains: 선택한 도메인 리스트.

    Returns:
        검색 쿼리 문자열.
    """
    # 도메인 키워드 추출
    domain_keywords = []
    for domain in domains:
        parts = domain.replace("/", " ").split()
        domain_keywords.extend(parts)

    domain_str = " ".join(domain_keywords)

    # user_input에서 불필요한 부분 제거 (질문형 어미 등)
    cleaned = user_input.strip()
    # "있나요?", "있을까요?", "추천해주세요" 등 제거
    cleaned = re.sub(
        r"(있나요|있을까요|알려주세요|추천해주세요|부탁합니다)[.?!]*$", "", cleaned
    ).strip()

    query = f"{domain_str} {cleaned}"

    logger.info(f"[ContextParser] Built search query: {query[:80]}...")
    return query


def _extract_goal(text: str) -> str:
    """목표 추출."""
    if any(kw in text for kw in ["이직", "전직", "경력 전환"]):
        return "이직"
    if any(kw in text for kw in ["전문성", "전문가", "심화", "스킬업", "역량"]):
        return "전문성 강화"
    if any(kw in text for kw in ["관심", "취미", "교양", "호기심"]):
        return "개인 관심"
    if any(kw in text for kw in ["창업", "사업", "프리랜서"]):
        return "창업"
    # 기본값: 취업 (가장 일반적)
    return "취업"


def _extract_employment_status(text: str) -> str:
    """고용 상태 추출."""
    if any(kw in text for kw in ["학생", "대학생", "졸업 전", "재학"]):
        return "학생"
    if any(kw in text for kw in ["직장", "재직", "회사", "다니", "근무", "현직"]):
        return "재직 중"
    if any(kw in text for kw in ["무직", "실업", "경력 단절"]):
        return "무직"
    # 기본값
    return "구직 중"


def _extract_major_background(text: str) -> str:
    """전공 배경 추출."""
    if any(kw in text for kw in ["비전공", "문과", "타전공"]):
        return "비전공자"
    if any(kw in text for kw in ["전공", "관련학과", "관련 전공"]):
        return "전공자"
    if any(kw in text for kw in ["경험", "경력", "실무"]):
        return "관련 경험 있음"
    # 기본값
    return "비전공자"


def _extract_weekly_hours(text: str, employment_status: str) -> int:
    """주당 학습 시간 추출."""
    # "주 N시간" 패턴
    match = re.search(r"주\s*(\d+)\s*시간", text)
    if match:
        hours = int(match.group(1))
        return max(1, min(40, hours))

    # 상태별 기본값
    if employment_status == "재직 중":
        return 10
    if employment_status == "학생":
        return 20
    return 15


def _extract_study_period(text: str) -> int:
    """준비 기간 추출 (일)."""
    # "N개월" 패턴
    match = re.search(r"(\d+)\s*개월", text)
    if match:
        months = int(match.group(1))
        return max(30, min(730, months * 30))

    # "N년" 패턴
    match = re.search(r"(\d+)\s*년", text)
    if match:
        years = int(match.group(1))
        return max(30, min(730, years * 365))

    # "단기", "빠르게" 등
    if any(kw in text for kw in ["단기", "빠르게", "빨리", "급하게"]):
        return 90

    # 기본값: 6개월
    return 180


def _extract_difficulty(text: str) -> str:
    """난이도 선호 추출."""
    if any(kw in text for kw in ["쉬운", "쉽게", "입문", "기초", "기능사"]):
        return "하"
    if any(kw in text for kw in ["어려운", "어렵", "고급", "전문", "기술사"]):
        return "상"
    if any(kw in text for kw in ["기사"]):
        return "중상"
    return "중"


def _extract_industries(domains: list[str]) -> list[str]:
    """도메인에서 선호 산업 추출."""
    industries = []
    for domain in domains:
        mapped = _DOMAIN_TO_INDUSTRIES.get(domain)
        if mapped:
            industries.extend(mapped)
        else:
            # 슬래시 분리
            parts = domain.replace("/", " ").split()
            industries.extend(parts)

    # 중복 제거, 최대 5개
    seen = set()
    unique = []
    for ind in industries:
        if ind not in seen:
            unique.append(ind)
            seen.add(ind)
    return unique[:5]
