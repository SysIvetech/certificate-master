"""검색 서비스 프로토콜 정의.

이 모듈은 검색 서비스의 공통 인터페이스를 정의합니다.
모든 검색 서비스 구현체(SearXNG 등)는 이 프로토콜을 따라야 합니다.
"""

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class SearchServiceProtocol(Protocol):
    """검색 서비스 프로토콜.

    모든 검색 서비스 구현체가 따라야 하는 인터페이스입니다.

    Attributes:
        provider_name: 검색 서비스 제공자 이름.
    """

    @property
    def provider_name(self) -> str:
        """검색 서비스 제공자 이름을 반환합니다.

        Returns:
            제공자 이름 (예: "searxng").
        """
        ...

    async def search(
        self,
        query: str,
        count: int = 5,
        country: str = "KR",
        search_lang: str = "ko",
    ) -> dict:
        """검색을 수행합니다.

        Args:
            query: 검색 질의 문자열.
            count: 반환할 결과 수(기본값: 5).
            country: 지역화 결과를 위한 국가 코드(기본값: KR).
            search_lang: 검색 언어(기본값: ko).

        Returns:
            검색 결과를 담은 딕셔너리. 최소한 다음 구조를 따름:
            {
                "web": {
                    "results": [
                        {
                            "title": str,
                            "url": str,
                            "description": str,
                            "age": str (optional),
                            "language": str (optional),
                        }
                    ]
                }
            }

        Raises:
            Exception: 검색이 실패한 경우.
        """
        ...

    async def search_certificate_comprehensive(
        self, certificate_title: str
    ) -> dict[str, list[dict]]:
        """여러 쿼리로 자격증 정보를 종합 검색합니다.

        Args:
            certificate_title: 자격증 한글명.

        Returns:
            카테고리별 검색 결과 딕셔너리:
            - general: 시험 기본 정보
            - statistics: 합격률 추이 및 준비기간 분포
            - career: 진로 및 활용 정보
            - reviews: 합격 후기 및 팁
            - study_methods: 학습 방법 및 계획
            - books: 추천 교재
            - lectures: 추천 강의
            - official: 공식 출처
        """
        ...

    async def search_study_plan_context(
        self,
        certificate_title: str,
        *,
        delay_seconds: float = 1.0,
    ) -> dict[str, list[dict]]:
        """학습 계획 프롬프트 보강용 정보를 검색합니다.

        Args:
            certificate_title: 자격증 한글명.
            delay_seconds: 속도 제한을 위한 쿼리 간 지연 시간.

        Returns:
            학습 계획에 맞춘 카테고리별 검색 결과 딕셔너리.
        """
        ...

    def format_search_results_for_llm(
        self,
        search_results: dict[str, list[dict]],
        categories: Optional[dict[str, str]] = None,
    ) -> str:
        """카테고리별 검색 결과를 LLM 입력 문자열로 포맷합니다.

        Args:
            search_results: 카테고리별 검색 결과 딕셔너리.
            categories: 선택 카테고리 표시 이름.

        Returns:
            모든 검색 결과를 담은 포맷 문자열.
        """
        ...
