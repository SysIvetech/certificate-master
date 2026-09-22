"""크롤러 프로토콜 정의.

이 모듈은 모든 크롤러 구현체가 따라야 하는 공통 인터페이스를 정의합니다.
Protocol 패턴을 사용하여 의존성 역전을 구현합니다.
"""

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable


@dataclass
class CrawlResult:
    """크롤링 결과를 담는 데이터 클래스.

    Attributes:
        content: 추출된 본문 콘텐츠.
        title: 페이지 제목.
        success: 크롤링 성공 여부.
        method: 사용된 크롤러 이름 (trafilatura, playwright).
        url: 크롤링된 URL.
        error: 실패 시 에러 메시지.
    """

    content: str
    title: str
    success: bool
    method: str
    url: str
    error: Optional[str] = None


@runtime_checkable
class CrawlerProtocol(Protocol):
    """크롤러 프로토콜.

    모든 크롤러 구현체가 따라야 하는 인터페이스입니다.

    Attributes:
        provider_name: 크롤러 제공자 이름 (trafilatura, playwright).
    """

    @property
    def provider_name(self) -> str:
        """크롤러 제공자 이름을 반환합니다.

        Returns:
            제공자 이름 (예: "trafilatura", "playwright").
        """
        ...

    async def extract_content(self, url: str) -> CrawlResult:
        """URL에서 본문 콘텐츠를 추출합니다.

        Args:
            url: 크롤링할 웹 페이지 URL.

        Returns:
            CrawlResult: 추출된 콘텐츠와 메타데이터.
        """
        ...

    def can_handle(self, url: str) -> bool:
        """이 크롤러가 해당 URL을 처리할 수 있는지 반환합니다.

        Args:
            url: 확인할 URL.

        Returns:
            bool: 처리 가능하면 True.
        """
        ...
