"""SearXNG 메타 검색 엔진 통합 서비스.

SearXNG을 사용하여 자격증 정보를 검색합니다.
다양한 검색 엔진의 결과를 집계하는 오픈소스 메타 검색 엔진입니다.

설치:
    docker run -d -p 8888:8080 searxng/searxng

사용법:
    service = get_searxng_service()
    results = await service.search_certificate_comprehensive("정보처리기사")
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.core.config import get_settings
from app.services.search.content_crawler import (
    ContentCrawlerService,
    get_content_crawler,
    is_crawlable_url,
)
from app.services.search.crawler.smart_crawler import (
    SmartCrawler,
    get_smart_crawler,
)
from app.services.search.query_generator import is_official_domain
from app.services.search.url_filter import (
    DomainFailureCache,
    is_valid_snippet,
)

logger = logging.getLogger(__name__)


def has_official_source(results: list[dict]) -> bool:
    """검색 결과에 공식 출처가 포함되어 있는지 확인합니다.

    Args:
        results: 검색 결과 목록.

    Returns:
        bool: 공식 출처가 포함되어 있으면 True.
    """
    if not results:
        return False

    for result in results:
        url = result.get("url", "")
        if is_official_domain(url):
            return True

    return False


class SearXNGSearchService:
    """SearXNG 메타 검색 엔진 통합 서비스.

    SearchServiceProtocol을 구현합니다.
    크롤링을 통해 검색 결과의 실제 콘텐츠를 추출할 수 있습니다.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        crawl_enabled: bool = True,
        crawl_top_n: int = 10,
        crawl_target_success: int = 3,
        use_smart_crawler: bool = True,
    ):
        """SearXNG 검색 서비스를 초기화합니다.

        Args:
            base_url: SearXNG 서버 URL. 제공되지 않으면 설정 값을 사용합니다.
            timeout: 요청 타임아웃(초). 제공되지 않으면 설정 값을 사용합니다.
            crawl_enabled: 크롤링 활성화 여부 (기본: True).
            crawl_top_n: 크롤링 시도할 최대 결과 수 (기본: 10).
            crawl_target_success: 크롤링 성공 목표 수 (기본: 3).
            use_smart_crawler: SmartCrawler 사용 여부 (기본: True).
        """
        settings = get_settings()
        self.base_url = base_url or settings.SEARXNG_BASE_URL
        self.timeout = timeout or settings.SEARXNG_TIMEOUT
        self._provider_name = "searxng"

        # 크롤링 설정
        self.crawl_enabled = crawl_enabled
        self.crawl_top_n = crawl_top_n
        self.crawl_target_success = crawl_target_success

        # SmartCrawler 설정
        self.use_smart_crawler = use_smart_crawler
        self._crawler: Optional[ContentCrawlerService] = None
        self._smart_crawler: Optional[SmartCrawler] = None

        # 도메인 실패 캐싱 (같은 도메인에서 연속 실패 시 크롤링 스킵)
        self._failure_cache = DomainFailureCache(max_failures=2)

    def _get_crawler(self):
        """크롤러 인스턴스를 반환합니다 (lazy initialization).

        use_smart_crawler가 True이면 SmartCrawler를,
        False이면 기존 ContentCrawlerService를 반환합니다.
        """
        if self.use_smart_crawler:
            if self._smart_crawler is None:
                self._smart_crawler = get_smart_crawler()
            return self._smart_crawler
        else:
            if self._crawler is None:
                self._crawler = get_content_crawler()
            return self._crawler

    def get_crawling_metrics(self) -> dict:
        """크롤링 메트릭을 반환합니다.

        SmartCrawler 사용 시 상세 메트릭을 반환하고,
        기존 크롤러 사용 시 기본 메트릭을 반환합니다.

        Returns:
            크롤링 메트릭 딕셔너리.
        """
        if self.use_smart_crawler and self._smart_crawler is not None:
            return self._smart_crawler.get_metrics_summary()
        else:
            return {
                "total_requests": 0,
                "trafilatura_success": 0,
                "playwright_success": 0,
                "fallback_count": 0,
                "failed_count": 0,
                "success_rate": 0.0,
            }

    @property
    def provider_name(self) -> str:
        """검색 서비스 제공자 이름을 반환합니다.

        Returns:
            제공자 이름 ("searxng").
        """
        return self._provider_name

    async def search(
        self,
        query: str,
        count: int = 5,
        country: str = "KR",
        search_lang: str = "ko",
    ) -> dict:
        """SearXNG으로 검색합니다.

        Args:
            query: 검색 질의 문자열.
            count: 반환할 결과 수 (기본: 5).
            country: 지역화를 위한 국가 코드 (기본: KR).
            search_lang: 검색 언어 (기본: ko).

        Returns:
            검색 결과 딕셔너리:
            {"web": {"results": [{"title", "url", "description", "age", "language"}]}}

        Raises:
            httpx.HTTPError: API 요청 실패 시.
        """
        language = self._get_language_code(search_lang, country)

        params = {
            "q": query,
            "format": "json",
            "language": language,
            "pageno": 1,
            "safesearch": 0,
            "categories": "general",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/search",
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])[:count]
        formatted_results = [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "description": r.get("content", ""),
                "age": self._format_relative_time(r.get("publishedDate", "")),
                "language": search_lang,
            }
            for r in results
        ]

        return {"web": {"results": formatted_results}}

    def _get_language_code(self, search_lang: str, country: str) -> str:
        """SearXNG 언어 코드를 반환합니다."""
        language_map = {
            "ko": "ko-KR",
            "en": "en-US",
            "ja": "ja-JP",
            "zh": "zh-CN",
        }
        return language_map.get(search_lang, f"{search_lang}-{country}")

    def _format_relative_time(self, date_str: str) -> str:
        """날짜를 상대적 시간 문자열로 변환합니다."""
        if not date_str:
            return ""

        try:
            dt = self._parse_date(date_str)
            if dt is None:
                return date_str

            now = datetime.now(timezone.utc)
            diff = now - dt

            if diff.days == 0:
                if diff.seconds < 3600:
                    return f"{diff.seconds // 60} minutes ago"
                return f"{diff.seconds // 3600} hours ago"
            elif diff.days == 1:
                return "1 day ago"
            elif diff.days < 7:
                return f"{diff.days} days ago"
            elif diff.days < 30:
                weeks = diff.days // 7
                return f"{weeks} week{'s' if weeks > 1 else ''} ago"
            elif diff.days < 365:
                months = diff.days // 30
                return f"{months} month{'s' if months > 1 else ''} ago"
            else:
                years = diff.days // 365
                return f"{years} year{'s' if years > 1 else ''} ago"

        except Exception:
            return date_str

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """날짜 문자열을 datetime으로 파싱합니다."""
        if "T" in date_str:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"]:
            try:
                return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    async def _ensure_official_source(
        self,
        certificate_title: str,
        results: dict[str, list[dict]],
    ) -> dict[str, list[dict]]:
        """공식 출처가 최소 1개 포함되도록 보장합니다.

        검색 결과에 공식 출처(Q-Net, HRD Korea 등)가 없으면
        site: 연산자를 사용한 fallback 검색을 수행합니다.

        Args:
            certificate_title: 자격증 한글명.
            results: 카테고리별 검색 결과 딕셔너리.

        Returns:
            공식 출처가 포함된 검색 결과 딕셔너리.
        """
        official_results = results.get("official", [])

        # 이미 공식 출처가 있는지 확인
        if has_official_source(official_results):
            logger.info("공식 출처가 이미 포함되어 있습니다.")
            return results

        # 다른 카테고리에서도 공식 출처 확인
        for category, category_results in results.items():
            if has_official_source(category_results):
                logger.info(f"공식 출처가 [{category}] 카테고리에 포함되어 있습니다.")
                return results

        # Fallback: site: 연산자로 직접 검색
        logger.warning("공식 출처가 없습니다. Fallback 검색을 수행합니다.")

        try:
            fallback_query = f"{certificate_title} site:q-net.or.kr"
            fallback_response = await self.search(fallback_query, count=3)
            fallback_results = self._extract_results(fallback_response)

            if fallback_results:
                # official 카테고리에 추가
                if "official" not in results:
                    results["official"] = []
                results["official"].extend(fallback_results)
                logger.info(
                    f"Fallback 검색으로 {len(fallback_results)}개 공식 출처 추가됨"
                )
            else:
                logger.warning("Fallback 검색에서도 공식 출처를 찾지 못했습니다.")

        except Exception as e:
            logger.error(f"Fallback 검색 실패: {e}")

        return results

    async def search_certificate_comprehensive(
        self, certificate_title: str
    ) -> dict[str, list[dict]]:
        """여러 쿼리로 자격증 정보를 종합 검색합니다.

        Args:
            certificate_title: 자격증 한글명.

        Returns:
            카테고리별 검색 결과 딕셔너리.
        """
        settings = get_settings()
        queries = self._build_comprehensive_queries(certificate_title)
        results = await self._run_categorized_queries(
            queries,
            delay_seconds=0.5,  # SearXNG은 로컬이므로 짧은 지연
            default_count=settings.SEARCH_RESULTS_PER_CATEGORY,
        )

        # 공식 출처 필수 확보
        if settings.SEARCH_OFFICIAL_SOURCE_REQUIRED:
            results = await self._ensure_official_source(certificate_title, results)

        return results

    async def search_study_plan_context(
        self,
        certificate_title: str,
        *,
        delay_seconds: float = 0.5,
    ) -> dict[str, list[dict]]:
        """학습 계획 프롬프트 보강용 정보를 검색합니다.

        Args:
            certificate_title: 자격증 한글명.
            delay_seconds: 속도 제한을 위한 쿼리 간 지연 시간.

        Returns:
            학습 계획에 맞춘 카테고리별 검색 결과 딕셔너리.
        """
        settings = get_settings()
        queries = self._build_study_plan_queries(certificate_title)
        return await self._run_categorized_queries(
            queries,
            delay_seconds=delay_seconds,
            default_count=settings.SEARCH_RESULTS_PER_CATEGORY,
        )

    def _extract_results(
        self,
        search_response: dict,
        keyword_hints: Optional[list[str]] = None,
    ) -> list[dict]:
        """검색 결과를 추출하고 품질 점수를 계산합니다.

        PDF, 파일 다운로드 URL은 제외합니다.

        Args:
            search_response: search() 메서드의 응답.
            keyword_hints: 관련성 점수 가중치를 위한 키워드.

        Returns:
            품질 점수가 포함된 결과 딕셔너리 목록.
        """
        web_results = search_response.get("web", {}).get("results", [])
        hints = keyword_hints or []

        extracted = []
        skipped_count = 0

        for result in web_results:
            url = result.get("url", "")

            # PDF/파일 다운로드 URL 필터링
            if not is_crawlable_url(url):
                skipped_count += 1
                continue

            text = f"{result.get('title', '')} {result.get('description', '')}"

            extracted.append(
                {
                    "title": result.get("title", ""),
                    "url": url,
                    "description": result.get("description", ""),
                    "age": result.get("age", ""),
                    "language": result.get("language", "ko"),
                    "url_quality": self._calculate_url_quality(url),
                    "recency_score": self._calculate_recency_score(
                        result.get("age", "")
                    ),
                    "keyword_score": self._calculate_keyword_score(text, hints),
                }
            )

        if skipped_count > 0:
            logger.debug(f"파일 다운로드 URL {skipped_count}개 제외됨")

        # 복합 점수 기반 정렬
        if hints:
            extracted.sort(
                key=lambda x: (
                    x["url_quality"] * 0.5
                    + x["recency_score"] * 0.3
                    + x["keyword_score"] * 0.2
                ),
                reverse=True,
            )
        else:
            extracted.sort(
                key=lambda x: x["url_quality"] * 0.6 + x["recency_score"] * 0.4,
                reverse=True,
            )

        return extracted

    async def _extract_results_with_crawl(
        self,
        search_response: dict,
        keyword_hints: Optional[list[str]] = None,
    ) -> list[dict]:
        """검색 결과를 추출하고 순차적으로 크롤링합니다.

        PDF/파일은 후순위로 정렬하고, 웹페이지를 우선 크롤링합니다.
        목표 성공 수(crawl_target_success)에 도달하면 크롤링을 중단합니다.
        크롤링 실패 시 검색 snippet을 fallback으로 사용합니다.

        최적화:
        - JS 렌더링 사이트는 크롤링 시도 없이 바로 snippet fallback
        - 동일 도메인에서 연속 실패 시 해당 도메인 크롤링 스킵
        - 품질이 낮은 snippet은 성공으로 카운트하지 않음

        Args:
            search_response: search() 메서드의 응답.
            keyword_hints: 관련성 점수 가중치를 위한 키워드.

        Returns:
            full_content 필드가 추가된 결과 딕셔너리 목록.
        """
        results = self._extract_results(search_response, keyword_hints)

        # 크롤링 비활성화 또는 결과 없음
        if not self.crawl_enabled or not results:
            for r in results:
                r["full_content"] = ""
                r["crawl_method"] = None
            return results

        # URL 우선순위 정렬 (PDF 후순위)
        prioritized = self._prioritize_urls(results)

        # 크롤링 결과 저장 (url -> content)
        crawled_content: dict[str, tuple[str, str]] = {}  # url -> (content, method)
        success_count = 0
        crawler = self._get_crawler()

        # 순차 크롤링: 성공 목표 수까지 시도
        for result in prioritized[: self.crawl_top_n]:
            if success_count >= self.crawl_target_success:
                break

            url = result["url"]
            description = result.get("description", "")

            # 도메인 실패 캐싱: 해당 도메인이 이미 여러 번 실패했으면 크롤링 스킵
            if self._failure_cache.should_skip(url):
                # 크롤링 스킵, 유효한 snippet이 있으면 사용
                if is_valid_snippet(description):
                    crawled_content[url] = (description, "snippet_fallback")
                    success_count += 1
                    logger.info(
                        f"도메인 캐시 스킵 + snippet ({success_count}/{self.crawl_target_success}): {url[:50]}"
                    )
                continue

            try:
                crawl_result = await crawler.extract_content(url)

                if crawl_result.success and crawl_result.content:
                    # 크롤링 성공
                    crawled_content[url] = (crawl_result.content, crawl_result.method)
                    success_count += 1
                    self._failure_cache.record_success(url)
                    logger.info(
                        f"크롤링 성공 ({success_count}/{self.crawl_target_success}): {url[:50]}"
                    )
                else:
                    # 크롤링 실패 → 실패 캐시 기록
                    self._failure_cache.record_failure(url)

                    # snippet fallback: 유효한 snippet만 성공으로 카운트
                    if is_valid_snippet(description):
                        crawled_content[url] = (description, "snippet_fallback")
                        success_count += 1
                        logger.info(
                            f"Snippet fallback ({success_count}/{self.crawl_target_success}): {url[:50]}"
                        )
                    else:
                        logger.warning(f"크롤링 실패 (유효한 snippet 없음): {url[:50]}")

            except Exception as e:
                logger.error(f"크롤링 예외: {url[:50]} - {e}")
                self._failure_cache.record_failure(url)

                if is_valid_snippet(description):
                    crawled_content[url] = (description, "snippet_fallback")
                    success_count += 1

        # 결과에 크롤링된 콘텐츠 병합
        for result in results:
            url = result["url"]
            if url in crawled_content:
                content, method = crawled_content[url]
                result["full_content"] = content
                result["crawl_method"] = method
            else:
                result["full_content"] = ""
                result["crawl_method"] = None

        return results

    def _prioritize_urls(self, results: list[dict]) -> list[dict]:
        """URL을 크롤링 우선순위로 정렬합니다.

        웹페이지를 우선하고, PDF/파일은 후순위로 정렬합니다.
        같은 우선순위 내에서는 원래 순서를 유지합니다 (stable sort).

        Args:
            results: 검색 결과 목록.

        Returns:
            우선순위로 정렬된 결과 목록.
        """
        file_extensions = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".hwp")

        def get_priority(result: dict) -> int:
            url = result.get("url", "").lower()
            # 파일 확장자 → 낮은 우선순위 (1)
            if url.endswith(file_extensions):
                return 1
            # 웹페이지 → 높은 우선순위 (0)
            return 0

        # stable sort로 같은 우선순위 내 순서 유지
        return sorted(results, key=get_priority)

    def _calculate_url_quality(self, url: str) -> int:
        """URL 품질 점수를 계산합니다 (0-100).

        우선순위:
        - 공식 정부/자격증 사이트: 100점
        - 채용 사이트: 95점
        - 교육 플랫폼: 90점
        - 뉴스: 75점
        - 교육 기관: 70점
        - 커뮤니티/블로그: 50점
        - 포럼: 40점
        - 기타: 60점
        """
        url_lower = url.lower()

        # 공식 정부/자격증 사이트
        official = ["q-net.or.kr", ".go.kr", "korcham.net", "hrdkorea.or.kr"]
        if any(d in url_lower for d in official):
            return 100

        # 채용 사이트
        job_sites = [
            "saramin.co.kr",
            "jobkorea.co.kr",
            "wanted.co.kr",
            "incruit.com",
            "career.co.kr",
        ]
        if any(d in url_lower for d in job_sites):
            return 95

        # 교육 플랫폼
        edu_platforms = ["eduwill.net", "hackers.com", "sdedu.co.kr", "ekac.or.kr"]
        if any(d in url_lower for d in edu_platforms):
            return 90

        # 뉴스 사이트
        news = [
            "naver.com/news",
            "daum.net/news",
            "chosun.com",
            "joongang.co.kr",
            "hani.co.kr",
        ]
        if any(d in url_lower for d in news):
            return 75

        # 교육 기관
        if any(d in url_lower for d in [".ac.kr", ".edu"]):
            return 70

        # 커뮤니티/블로그
        community = ["naver.com/cafe", "blog.naver.com", "tistory.com", "brunch.co.kr"]
        if any(d in url_lower for d in community):
            return 50

        # 포럼
        forums = ["dcinside.com", "clien.net", "todayhumor.co.kr"]
        if any(d in url_lower for d in forums):
            return 40

        return 60

    def _calculate_recency_score(self, age: str) -> int:
        """최신성 점수를 계산합니다 (0-100)."""
        if not age:
            return 50

        age_lower = age.lower()

        # 매우 최신
        if any(term in age_lower for term in ["hour", "시간", "minute", "분"]):
            return 100
        if any(term in age_lower for term in ["day", "일", "today", "오늘"]):
            return 95
        if "week" in age_lower or "주" in age_lower:
            return 85

        # 최신
        if any(term in age_lower for term in ["month", "개월", "달"]):
            try:
                months = int("".join(filter(str.isdigit, age_lower)))
                return max(40, 80 - (months * 10))
            except ValueError:
                return 60

        # 오래됨
        if "year" in age_lower or "년" in age_lower:
            try:
                years = int("".join(filter(str.isdigit, age_lower)))
                return max(10, 50 - (years * 15))
            except ValueError:
                return 30

        return 50

    def _calculate_keyword_score(self, text: str, keywords: list[str]) -> int:
        """키워드 매칭 관련성 점수를 계산합니다 (0-100)."""
        if not text or not keywords:
            return 0

        text_lower = text.lower()
        hits = sum(1 for kw in keywords if kw.lower().strip() in text_lower)

        if hits == 0:
            return 0

        return min(100, int(100 * hits / max(len(keywords), 1)))

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
        output = "=== 자격증 정보 검색 결과 ===\n\n"

        categories = categories or {
            "general": "1. 시험 기본 정보",
            "statistics": "2. 합격률 및 준비기간 통계",
            "career": "3. 진로 및 활용",
            "reviews": "4. 합격 후기 및 팁",
            "study_methods": "5. 학습 방법 및 계획",
            "books": "6. 추천 교재",
            "lectures": "7. 추천 강의",
            "official": "8. 공식 출처",
            "exam_schedule": "9. 시험 일정",
            "job_postings": "10. 채용공고 우대 조건",
            "public_sector": "11. 공무원/공기업 가산점",
            "cost_breakdown": "12. 비용 정보",
            "non_major_reviews": "13. 비전공자 합격 후기",
            "free_resources": "14. 기출문제/무료 자료",
            "comparison": "15. 유사 자격증 비교",
        }

        for category_key, category_name in categories.items():
            results = search_results.get(category_key, [])

            output += f"## {category_name}\n\n"

            if not results:
                output += "  (검색 결과 없음)\n\n"
                continue

            for idx, result in enumerate(results, 1):
                output += f"[{category_key.upper()}-{idx}]\n"
                output += f"제목: {result['title']}\n"
                output += f"URL: {result['url']}\n"

                url_quality = result.get("url_quality", 0)
                if url_quality >= 90:
                    output += "출처: 공식 사이트 [***]\n"
                elif url_quality >= 70:
                    output += "출처: 신뢰할 수 있는 사이트 [**]\n"
                elif url_quality >= 50:
                    output += "출처: 참고용 [*]\n"

                # full_content가 있으면 우선 사용, 없으면 description 사용
                full_content = result.get("full_content", "")
                if full_content:
                    output += f"요약: {result['description']}\n"
                    output += f"상세 내용:\n{full_content}\n"
                    if result.get("crawl_method"):
                        output += f"(크롤링: {result['crawl_method']})\n"
                else:
                    output += f"내용: {result['description']}\n"

                if result.get("age"):
                    output += f"최근성: {result['age']}"
                    recency = result.get("recency_score", 0)
                    if recency >= 80:
                        output += " (최신 정보)\n"
                    elif recency < 40:
                        output += " (오래된 정보 주의)\n"
                    else:
                        output += "\n"

                output += "\n"

        output += "=== 검색 종료 ===\n"
        total_results = sum(len(results) for results in search_results.values())
        output += f"총 {total_results}개의 자료 수집됨"

        return output

    def _build_comprehensive_queries(self, certificate_title: str) -> dict[str, dict]:
        """자격증 보강용 확장 쿼리를 생성합니다.

        취업준비생 관점의 카테고리 포함:
        - job_postings: 채용공고 우대/필수 조건
        - public_sector: 공무원/공기업 가산점
        - cost_breakdown: 총 비용 (교재+인강+응시료)
        - non_major_reviews: 비전공자/직장인 합격기
        - free_resources: 기출문제/무료 자료
        - comparison: 유사 자격증 비교

        Args:
            certificate_title: 자격증 한글명.

        Returns:
            카테고리별 쿼리 딕셔너리.
        """
        return {
            "general": {
                "query": f"{certificate_title} 자격증 시험 과목 합격기준 응시료",
                "keywords": ["시험", "과목", "합격 기준", "응시료", "시험 시간"],
            },
            "statistics": {
                "query": f"{certificate_title} 자격증 합격률 공부기간 평균",
                "keywords": ["합격률", "응시자", "통계", "공부기간", "준비기간"],
            },
            "career": {
                "query": f"{certificate_title} 자격증 연봉 통계 취업 전망",
                "keywords": ["연봉", "취업", "전망", "직무", "커리어"],
            },
            "reviews": {
                "query": f"{certificate_title} 자격증 합격 후기 공부법 난이도 팁",
                "keywords": ["합격 후기", "공부법", "난이도", "팁", "경험담"],
            },
            "study_methods": {
                "query": f"{certificate_title} 자격증 공부 순서 학습 계획 단계별",
                "keywords": ["공부 순서", "학습 계획", "단계", "시간 배분", "교재"],
            },
            "books": {
                "query": f"{certificate_title} 자격증 추천 교재 교재명 출판사",
                "keywords": ["교재", "수험서", "추천", "출판사"],
            },
            "lectures": {
                "query": f"{certificate_title} 자격증 인강 추천 강의",
                "keywords": ["인강", "강의", "커리큘럼", "수강"],
            },
            "official": {
                "query": f"{certificate_title} 자격증 큐넷 한국산업인력공단",
                "keywords": ["공식", "큐넷", "한국산업인력공단", "공고"],
            },
            # 취업준비생 관점 카테고리 (NEW)
            "job_postings": {
                "query": f"{certificate_title} 자격증 채용공고 우대 필수 가산점 모집",
                "keywords": ["채용", "우대", "필수", "가산점", "모집", "자격요건"],
            },
            "public_sector": {
                "query": f"{certificate_title} 자격증 공무원 공기업 가산점 NCS 공채",
                "keywords": ["공무원", "공기업", "가산점", "NCS", "공채", "필기"],
            },
            "cost_breakdown": {
                "query": f"{certificate_title} 자격증 비용 교재 가격 인강 가격 응시료 총비용",
                "keywords": ["비용", "가격", "교재", "인강", "응시료", "총비용"],
            },
            "non_major_reviews": {
                "query": f"{certificate_title} 비전공자 합격 후기 직장인 독학 문과 0베이스",
                "keywords": ["비전공자", "직장인", "독학", "문과", "0베이스", "초시생"],
            },
            "free_resources": {
                "query": f"{certificate_title} 기출문제 무료 풀이 해설 유튜브 블로그",
                "keywords": ["기출문제", "무료", "풀이", "해설", "유튜브", "블로그"],
            },
            "comparison": {
                "query": f"{certificate_title} vs 비교 차이점 어떤 자격증 선택",
                "keywords": ["vs", "비교", "차이점", "어떤", "선택", "추천"],
            },
            # 시험 일정 카테고리 (NEW)
            "exam_schedule": {
                "query": f"{certificate_title} 시험 일정 접수 기간 2025 2026",
                "keywords": [
                    "시험 일정",
                    "접수 기간",
                    "시행계획",
                    "공고",
                    "시험일",
                    "원서접수",
                ],
            },
        }

    def _build_study_plan_queries(self, certificate_title: str) -> dict[str, dict]:
        """학습 계획 관련 신호 수집 쿼리를 생성합니다.

        Args:
            certificate_title: 자격증 한글명.

        Returns:
            카테고리별 쿼리 딕셔너리.
        """
        return {
            "exam_schedule": {
                "query": f"{certificate_title} 시험 일정 접수 기간",
                "keywords": ["시험 일정", "접수 기간", "시행계획", "공고", "시험일"],
            },
            "exam_structure": {
                "query": f"{certificate_title} 과목 배점 문항 수 시험 시간",
                "keywords": ["과목", "배점", "문항", "시험 시간", "합격 기준"],
            },
            "pass_rate": {
                "query": f"{certificate_title} 합격률 응시자 수 통계",
                "keywords": ["합격률", "응시자", "통계", "추이"],
            },
            "study_period": {
                "query": f"{certificate_title} 준비기간 평균 공부기간",
                "keywords": ["준비기간", "공부기간", "평균", "개월"],
            },
            "study_plan_examples": {
                "query": f"{certificate_title} 합격 수기 공부 계획 주차별",
                "keywords": ["합격 수기", "공부 계획", "주차별", "시간표"],
            },
            "learning_sequence": {
                "query": f"{certificate_title} 공부 순서 학습 순서 커리큘럼",
                "keywords": ["공부 순서", "학습 순서", "커리큘럼", "단계"],
            },
            "time_allocation": {
                "query": f"{certificate_title} 이론 실전 복습 시간 배분",
                "keywords": ["이론", "실전", "복습", "시간 배분", "비율"],
            },
            "weak_subjects": {
                "query": f"{certificate_title} 과목별 난이도 취약 과목",
                "keywords": ["과목별", "난이도", "취약", "전략"],
            },
            "mock_exams": {
                "query": f"{certificate_title} 기출문제 모의고사 오답노트",
                "keywords": ["기출문제", "모의고사", "오답노트", "반복"],
            },
            "official": {
                "query": f"{certificate_title} 자격증 큐넷 한국산업인력공단",
                "keywords": ["공식", "큐넷", "한국산업인력공단", "공고"],
            },
        }

    async def _run_categorized_queries(
        self,
        queries: dict[str, dict],
        *,
        delay_seconds: float,
        default_count: int = 10,
        enable_crawl: bool = True,
    ) -> dict[str, list[dict]]:
        """카테고리별 쿼리를 실행합니다.

        Args:
            queries: 카테고리별 쿼리 딕셔너리.
            delay_seconds: 쿼리 간 지연 시간.
            default_count: 기본 결과 수.
            enable_crawl: 크롤링 활성화 여부.

        Returns:
            카테고리별 검색 결과 딕셔너리.
        """
        # 새로운 검색 세션 시작 시 실패 캐시 초기화
        self._failure_cache.clear()

        results = {}

        for category, payload in queries.items():
            query = payload["query"]
            query_count = payload.get("count", default_count)
            keywords = payload.get("keywords", [])

            try:
                logger.info(f"[{category}] 검색: {query[:50]}...")

                search_result = await self.search(query, count=query_count)
                result_count = len(search_result.get("web", {}).get("results", []))
                logger.info(f"[{category}] {result_count}개 결과")

                if enable_crawl and self.crawl_enabled:
                    results[category] = await self._extract_results_with_crawl(
                        search_result, keyword_hints=keywords
                    )
                    crawled = sum(1 for r in results[category] if r.get("full_content"))
                    logger.info(f"[{category}] 크롤링: {crawled}/{self.crawl_top_n}")
                else:
                    results[category] = self._extract_results(
                        search_result, keyword_hints=keywords
                    )

            except Exception as e:
                logger.error(f"[{category}] 검색 오류: {e}")
                results[category] = []

            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)

        return results


# 싱글턴 인스턴스
_searxng_service: Optional[SearXNGSearchService] = None


def get_searxng_service() -> SearXNGSearchService:
    """싱글턴 SearXNG 서비스 인스턴스를 반환합니다."""
    global _searxng_service
    if _searxng_service is None:
        _searxng_service = SearXNGSearchService()
    return _searxng_service
