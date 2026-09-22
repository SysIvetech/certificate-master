"""동적 검색 쿼리 생성기.

이 모듈은 자격증 유형별로 최적화된 검색 쿼리를 생성합니다.
공식 출처(Q-Net 등)를 필수로 포함하고, 카테고리별 맞춤 쿼리를 제공합니다.
"""

from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

# 공식 자격증 정보 도메인
OFFICIAL_DOMAINS: set[str] = {
    "q-net.or.kr",  # 한국산업인력공단 큐넷
    "hrdkorea.or.kr",  # 한국산업인력공단
    "kpc.or.kr",  # 한국생산성본부
    "ihd.or.kr",  # 한국정보통신진흥협회
    "kcqa.or.kr",  # 한국정보통신자격협회
}


def is_official_domain(url: str) -> bool:
    """URL이 공식 자격증 정보 도메인인지 확인합니다.

    Args:
        url: 확인할 URL.

    Returns:
        bool: 공식 도메인이면 True.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # www. 접두사 제거
        if domain.startswith("www."):
            domain = domain[4:]

        # 정확한 도메인 일치 확인
        if domain in OFFICIAL_DOMAINS:
            return True

        # 서브도메인 포함 확인
        for official_domain in OFFICIAL_DOMAINS:
            if domain.endswith("." + official_domain):
                return True

        return False

    except Exception:
        return False


@dataclass
class QueryConfig:
    """검색 쿼리 설정.

    Attributes:
        query: 검색 쿼리 문자열.
        keywords: 결과 필터링용 키워드 목록.
        priority: 쿼리 우선순위 (high, normal, low).
        required: 필수 쿼리 여부 (True면 결과가 없을 때 재시도).
    """

    query: str
    keywords: list[str] = field(default_factory=list)
    priority: str = "normal"
    required: bool = False


class QueryGenerator:
    """자격증 유형별 최적화된 검색 쿼리 생성기.

    자격증 종류에 따라 적절한 검색 쿼리를 생성합니다.
    공식 출처(Q-Net 등)를 필수로 포함하고,
    카테고리별로 맞춤화된 쿼리를 제공합니다.

    Attributes:
        title: 자격증명.
        type: 자격증 유형 (국가기술, 국가전문, 민간 등).
    """

    def __init__(
        self,
        certificate_title: str,
        certificate_type: Optional[str] = None,
    ):
        """QueryGenerator를 초기화합니다.

        Args:
            certificate_title: 자격증 한글명.
            certificate_type: 자격증 유형 (국가기술, 국가전문, 민간 등).
        """
        self.title = certificate_title
        self.type = certificate_type

    def build_queries(self) -> dict[str, QueryConfig]:
        """카테고리별 검색 쿼리를 생성합니다.

        Returns:
            카테고리명을 키로, QueryConfig를 값으로 하는 딕셔너리.
        """
        queries = {}

        # 1. 공식 출처 쿼리 (필수)
        queries["official"] = self._build_official_query()

        # 2. 기본 정보 쿼리
        queries["general"] = QueryConfig(
            query=f"{self.title} 시험 정보 개요 응시자격",
            keywords=["시험", "일정", "응시자격", "접수"],
            priority="high",
        )

        # 3. 통계 쿼리
        queries["statistics"] = QueryConfig(
            query=f"{self.title} 합격률 통계 난이도",
            keywords=["합격률", "통계", "난이도", "추이"],
            priority="normal",
        )

        # 4. 진로/활용 쿼리
        queries["career"] = QueryConfig(
            query=f"{self.title} 취업 연봉 진로 활용",
            keywords=["취업", "연봉", "진로", "활용", "전망"],
            priority="normal",
        )

        # 5. 합격 후기 쿼리
        queries["reviews"] = QueryConfig(
            query=f"{self.title} 합격 후기 공부법 팁",
            keywords=["합격", "후기", "공부법", "팁", "경험"],
            priority="normal",
        )

        # 6. 학습 방법 쿼리
        queries["study_methods"] = QueryConfig(
            query=f"{self.title} 학습 방법 공부 계획 독학",
            keywords=["학습", "공부", "계획", "독학", "인강"],
            priority="normal",
        )

        # 7. 추천 교재 쿼리
        queries["books"] = QueryConfig(
            query=f"{self.title} 추천 교재 책 기출문제",
            keywords=["교재", "책", "기출", "문제집"],
            priority="low",
        )

        # 8. 추천 강의 쿼리
        queries["lectures"] = QueryConfig(
            query=f"{self.title} 인강 강의 추천 온라인",
            keywords=["인강", "강의", "온라인", "학원"],
            priority="low",
        )

        return queries

    def _build_official_query(self) -> QueryConfig:
        """공식 출처 검색 쿼리를 생성합니다.

        자격증 유형에 따라 적절한 공식 사이트를 타겟팅합니다.

        Returns:
            공식 출처용 QueryConfig.
        """
        # 기본적으로 Q-Net과 HRD Korea를 포함
        site_operators = "site:q-net.or.kr OR site:hrdkorea.or.kr"

        # 국가전문자격의 경우 추가 사이트
        if self.type == "국가전문":
            # 국가전문자격은 해당 협회 사이트도 포함할 수 있음
            pass

        return QueryConfig(
            query=f"{self.title} {site_operators}",
            keywords=["공식", "큐넷", "한국산업인력공단", "시험일정"],
            priority="high",
            required=True,
        )

    def get_fallback_official_query(self) -> str:
        """공식 출처 fallback 쿼리를 반환합니다.

        공식 출처 검색 결과가 없을 때 사용합니다.

        Returns:
            site: 연산자를 사용한 fallback 쿼리.
        """
        return f"{self.title} site:q-net.or.kr"
