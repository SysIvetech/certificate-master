"""URL 필터링 및 품질 검증 모듈.

이 모듈은 크롤링 효율성을 높이기 위한 필터링 기능을 제공합니다:
1. JS 렌더링 사이트 사전 감지 - 크롤링 시도 없이 바로 snippet 사용
2. Snippet 품질 검증 - 의미 없는 snippet 필터링
3. 도메인별 실패 캐싱 - 반복 실패 방지

Note:
    블랙리스트/실패 캐싱은 "크롤링만 스킵"하고 snippet은 계속 사용합니다.
    따라서 데이터 손실 없이 처리 속도만 개선됩니다.
"""

from typing import Optional
from urllib.parse import urlparse

# ============================================================
# JS 렌더링 사이트 감지
# ============================================================

# 크롤링이 항상 실패하는 JS 렌더링 사이트 목록
# 이 사이트들은 크롤링을 시도하지 않고 바로 snippet을 사용합니다.
#
# 주의: 공식 사이트(q-net.or.kr 등)는 여기에 포함하지 않습니다.
# - 공식 사이트는 일부 페이지가 성공할 수 있음
# - 실패해도 snippet fallback이 작동하므로 데이터 손실 없음
# - DomainFailureCache가 연속 실패 시 자동으로 스킵 처리
_JS_RENDERED_DOMAINS: set[str] = {
    # 채용 사이트 (모바일/SPA) - 항상 JS 렌더링
    "m.jobkorea.co.kr",
    "m.saramin.co.kr",
    # 소셜/커뮤니티 (SPA) - 항상 JS 렌더링
    "story.kakao.com",
}


# ============================================================
# Playwright 필요 도메인 목록
# ============================================================

# Playwright가 필요한 도메인 목록
# 이 도메인들은 Trafilatura로 콘텐츠 추출이 불가능하며
# Playwright를 사용해야 합니다.
PLAYWRIGHT_DOMAINS: set[str] = {
    # 채용 사이트 (SPA/React 기반)
    "jobkorea.co.kr",
    "saramin.co.kr",
    "wanted.co.kr",
    "incruit.com",
    # 소셜/커뮤니티 (SPA)
    "story.kakao.com",
    "brunch.co.kr",
}


def is_js_rendered_domain(url: str) -> bool:
    """URL이 JS 렌더링 사이트인지 확인합니다.

    JS 렌더링 사이트는 trafilatura로 콘텐츠를 추출할 수 없으므로
    크롤링을 시도하지 않고 바로 snippet fallback을 사용합니다.

    Args:
        url: 확인할 URL.

    Returns:
        bool: JS 렌더링 사이트이면 True.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # 정확한 도메인 일치 확인
        if domain in _JS_RENDERED_DOMAINS:
            return True

        # 서브도메인 포함 확인 (예: www.q-net.or.kr -> q-net.or.kr)
        for js_domain in _JS_RENDERED_DOMAINS:
            if domain.endswith("." + js_domain) or domain == js_domain:
                return True

        return False

    except Exception:
        return False


# ============================================================
# Snippet 품질 검증
# ============================================================

# 의미 없는 snippet에 포함되는 패턴
_INVALID_SNIPPET_PATTERNS: list[str] = [
    "로딩 중",
    "로딩중",
    "Loading",
    "JavaScript를 활성화",
    "JavaScript가 필요",
    "자바스크립트를 활성화",
    "페이지를 찾을 수 없",
    "Page not found",
    "404",
    "접근 불가",
    "접근이 거부",
    "권한이 없습니다",
    "로그인이 필요",
    "로그인 후",
]


def is_valid_snippet(snippet: Optional[str], min_length: int = 50) -> bool:
    """Snippet이 유효한지 확인합니다.

    유효하지 않은 snippet:
    - None 또는 빈 문자열
    - 최소 길이 미만
    - 의미 없는 패턴 포함 (로딩 중, JavaScript 필요 등)

    Args:
        snippet: 검증할 snippet 텍스트.
        min_length: 최소 길이 (기본: 50자).

    Returns:
        bool: 유효하면 True.
    """
    if not snippet:
        return False

    stripped = snippet.strip()

    # 최소 길이 검증
    if len(stripped) < min_length:
        return False

    # 의미 없는 패턴 검증
    snippet_lower = stripped.lower()
    for pattern in _INVALID_SNIPPET_PATTERNS:
        if pattern.lower() in snippet_lower:
            return False

    return True


# ============================================================
# 도메인별 실패 캐싱
# ============================================================


class DomainFailureCache:
    """도메인별 크롤링 실패를 캐싱하여 반복 시도를 방지합니다.

    동일 도메인에서 연속으로 실패하면 해당 도메인의 크롤링을 스킵하고
    바로 snippet fallback을 사용합니다.

    Note:
        이 캐시는 세션(파이프라인 실행) 단위로 동작합니다.
        새 파이프라인 실행 시 캐시가 초기화됩니다.

    Attributes:
        max_failures: 스킵 전 허용되는 최대 실패 횟수.

    Example:
        >>> cache = DomainFailureCache(max_failures=2)
        >>> cache.record_failure("https://example.com/page1")
        >>> cache.record_failure("https://example.com/page2")
        >>> cache.should_skip("https://example.com/page3")
        True  # 2번 실패 후 스킵
    """

    def __init__(self, max_failures: int = 2):
        """DomainFailureCache를 초기화합니다.

        Args:
            max_failures: 스킵 전 허용되는 최대 실패 횟수 (기본: 2).
        """
        self.max_failures = max_failures
        self._failures: dict[str, int] = {}

    def _extract_domain(self, url: str) -> str:
        """URL에서 도메인을 추출합니다."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""

    def should_skip(self, url: str) -> bool:
        """해당 URL의 도메인을 스킵해야 하는지 확인합니다.

        Args:
            url: 확인할 URL.

        Returns:
            bool: 스킵해야 하면 True.
        """
        domain = self._extract_domain(url)
        if not domain:
            return False

        return self._failures.get(domain, 0) >= self.max_failures

    def record_failure(self, url: str) -> None:
        """크롤링 실패를 기록합니다.

        Args:
            url: 실패한 URL.
        """
        domain = self._extract_domain(url)
        if domain:
            self._failures[domain] = self._failures.get(domain, 0) + 1

    def record_success(self, url: str) -> None:
        """크롤링 성공을 기록하고 해당 도메인의 실패 카운트를 초기화합니다.

        Args:
            url: 성공한 URL.
        """
        domain = self._extract_domain(url)
        if domain and domain in self._failures:
            self._failures[domain] = 0

    def get_failure_count(self, url: str) -> int:
        """해당 URL 도메인의 실패 횟수를 반환합니다.

        Args:
            url: 확인할 URL.

        Returns:
            int: 실패 횟수.
        """
        domain = self._extract_domain(url)
        return self._failures.get(domain, 0)

    def clear(self) -> None:
        """캐시를 초기화합니다."""
        self._failures.clear()


# ============================================================
# 싱글턴 인스턴스 (선택적 사용)
# ============================================================

_global_failure_cache: Optional[DomainFailureCache] = None


def get_domain_failure_cache() -> DomainFailureCache:
    """전역 DomainFailureCache 인스턴스를 반환합니다.

    Returns:
        DomainFailureCache 인스턴스.
    """
    global _global_failure_cache
    if _global_failure_cache is None:
        _global_failure_cache = DomainFailureCache()
    return _global_failure_cache


def reset_domain_failure_cache() -> None:
    """전역 DomainFailureCache를 리셋합니다."""
    global _global_failure_cache
    if _global_failure_cache is not None:
        _global_failure_cache.clear()


# ============================================================
# Playwright 필요 여부 판단
# ============================================================


def is_playwright_required(url: str) -> bool:
    """URL이 Playwright가 필요한지 확인합니다.

    Playwright가 필요한 경우:
    - 채용 사이트 (jobkorea, saramin, wanted, incruit)
    - SPA 기반 소셜/커뮤니티 사이트 (kakao story, brunch)

    Args:
        url: 확인할 URL.

    Returns:
        bool: Playwright가 필요하면 True.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # www. 접두사 제거
        if domain.startswith("www."):
            domain = domain[4:]

        # 모바일 서브도메인 제거 (m.jobkorea.co.kr -> jobkorea.co.kr)
        if domain.startswith("m."):
            domain = domain[2:]

        # 정확한 도메인 일치 확인
        if domain in PLAYWRIGHT_DOMAINS:
            return True

        # 서브도메인 포함 확인 (예: job.incruit.com -> incruit.com)
        for pw_domain in PLAYWRIGHT_DOMAINS:
            if domain.endswith("." + pw_domain):
                return True

        return False

    except Exception:
        return False
