"""구조화된 입력에서 검색 쿼리 및 메타데이터 필터를 생성합니다.

Contextual Retrieval 전략의 핵심:
- 구조화된 사용자 입력 -> Contextual Prefix와 동일한 어휘의 쿼리 생성
- 쿼리와 문서가 같은 "언어"를 사용하여 유사도 향상
"""

from typing import Optional

# 상황 -> 대상 사용자 매핑 (Contextual Prefix와 동일한 어휘 사용)
_STATUS_TARGET_MAP: dict[str, str] = {
    "학생": "비전공자·입문자",
    "취준생": "비전공자",
    "직장인": "직장인·경력자",
    "경력자": "경력자·전문가",
    "전업 준비": "비전공자·직장인",
}


def build_structured_query(
    domains: list[str],
    purpose: str,
    current_status: str,
    preference_tags: list[str] | None = None,
    additional_input: str = "",
) -> str:
    """구조화된 입력에서 Contextual Prefix와 매칭되는 검색 쿼리를 생성합니다.

    Args:
        domains: 관심 분야 리스트.
        purpose: 목적 (취업, 이직, 전문성 강화 등).
        current_status: 현재 상황 (학생, 직장인 등).
        preference_tags: 선호 태그 리스트 (선택).
        additional_input: 추가 자유 입력 (선택).

    Returns:
        검색 쿼리 문자열.
    """
    preference_tags = preference_tags or []
    domain_text = ", ".join(domains)
    target = _STATUS_TARGET_MAP.get(current_status, "")

    parts = [
        f"{domain_text} 분야",
        f"{target}에게 적합하며" if target else "",
        f"{purpose}에 도움이 되는 자격증",
    ]

    for tag in preference_tags:
        if tag == "독학 가능":
            parts.append("독학 가능")
        elif tag == "비전공자":
            parts.append("비전공자에게 적합")
        elif tag == "비용 저렴":
            parts.append("비용 20만원 이하")
        elif tag == "CBT 상시시험":
            parts.append("CBT 상시시험")

    query = " ".join(filter(None, parts))

    if additional_input and additional_input.strip():
        query += f" {additional_input.strip()}"

    return query


def build_structured_metadata_filter(
    preference_tags: list[str] | None = None,
    current_status: str = "",
) -> Optional[dict]:
    """구조화된 입력에서 ChromaDB where 필터를 생성합니다.

    Args:
        preference_tags: 선호 태그 리스트.
        current_status: 현재 상황.

    Returns:
        ChromaDB where 필터 딕셔너리 또는 None.
    """
    preference_tags = preference_tags or []
    filters = []

    if "독학 가능" in preference_tags or "비전공자" in preference_tags:
        filters.append({"non_major_friendly": True})
    if "CBT 상시시험" in preference_tags:
        filters.append({"cbt_available": True})

    if not filters:
        return None
    if len(filters) == 1:
        return filters[0]
    return {"$and": filters}
