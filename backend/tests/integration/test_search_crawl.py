"""검색 및 크롤링 결과 테스트 스크립트.

이 스크립트는 검색 서비스의 크롤링 기능을 테스트하고
결과를 확인할 수 있도록 합니다.

사용법:
    # 기본 테스트 (크롤링 포함)
    uv run python -m scripts.test_search_crawl

    # 특정 자격증 테스트
    uv run python -m scripts.test_search_crawl --cert "정보처리기사"

    # 크롤링 비활성화
    uv run python -m scripts.test_search_crawl --no-crawl

    # 상세 출력
    uv run python -m scripts.test_search_crawl --verbose
"""

import argparse
import asyncio
import io
import sys
from datetime import datetime
from pathlib import Path

# Windows 콘솔 UTF-8 출력 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.services.content_crawler import ContentCrawlerService
from app.services.search_factory import get_search_service


async def test_single_crawl(url: str) -> None:
    """단일 URL 크롤링 테스트."""
    print(f"\n{'='*60}")
    print("단일 URL 크롤링 테스트")
    print(f"{'='*60}")
    print(f"URL: {url}")

    crawler = ContentCrawlerService()
    result = await crawler.extract_content(url)

    print("\n결과:")
    print(f"  성공: {result.success}")
    print(f"  방법: {result.method}")
    print(f"  제목: {result.title}")
    print(f"  콘텐츠 길이: {len(result.content)} 자")

    if result.success:
        print("\n콘텐츠 미리보기 (처음 500자):")
        print("-" * 40)
        print(result.content[:500])
        if len(result.content) > 500:
            print("...")
    else:
        print(f"  에러: {result.error}")


async def test_search_with_crawl(
    certificate_title: str,
    crawl_enabled: bool = True,
    verbose: bool = False,
) -> None:
    """검색 및 크롤링 통합 테스트."""
    settings = get_settings()

    print(f"\n{'='*60}")
    print("[TEST] 검색 및 크롤링 통합 테스트")
    print(f"{'='*60}")
    print(f"[CONFIG] 자격증: {certificate_title}")
    print(f"[CONFIG] 검색 프로바이더: {settings.SEARCH_PROVIDER}")
    print(f"[CONFIG] 크롤링 활성화: {crawl_enabled}")
    print(f"[CONFIG] 카테고리당 크롤링 수: {settings.CRAWL_TOP_N}")
    print(f"[CONFIG] 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sys.stdout.flush()

    # 검색 서비스 생성
    print("\n[INIT] 검색 서비스 초기화 중...")
    sys.stdout.flush()
    search_service = get_search_service()

    # 크롤링 설정 적용
    search_service.crawl_enabled = crawl_enabled
    search_service.crawl_top_n = settings.CRAWL_TOP_N
    print("[INIT] 검색 서비스 준비 완료")
    sys.stdout.flush()

    print("\n[START] 검색 및 크롤링 시작...")
    sys.stdout.flush()
    start_time = datetime.now()

    # 종합 검색 실행 (실시간 로그는 _run_categorized_queries에서 출력됨)
    search_results = await search_service.search_certificate_comprehensive(
        certificate_title
    )

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\n[DONE] 검색 완료! (총 소요 시간: {elapsed:.1f}초)")
    sys.stdout.flush()

    # 결과 요약
    print(f"\n{'='*60}")
    print("결과 요약")
    print(f"{'='*60}")

    total_results = 0
    total_crawled = 0

    for category, results in search_results.items():
        crawled_count = sum(1 for r in results if r.get("full_content"))
        total_results += len(results)
        total_crawled += crawled_count

        print(f"\n[{category}]")
        print(f"  검색 결과: {len(results)}개")
        print(f"  크롤링 성공: {crawled_count}개")

        if verbose and results:
            for i, result in enumerate(results[:3]):  # 상위 3개만 표시
                print(f"\n  [{i+1}] {result['title']}")
                print(f"      URL: {result['url']}")
                print(f"      URL 품질: {result.get('url_quality', 'N/A')}")

                if result.get("full_content"):
                    content_preview = result["full_content"][:200]
                    print(f"      크롤링: {result.get('crawl_method', 'N/A')}")
                    print(f"      콘텐츠 ({len(result['full_content'])}자):")
                    print(f"        {content_preview}...")
                else:
                    desc = result["description"][:100]
                    print(f"      설명: {desc}...")

    print(f"\n{'='*60}")
    print(f"총 검색 결과: {total_results}개")
    print(f"총 크롤링 성공: {total_crawled}개")
    print(f"크롤링 성공률: {total_crawled/max(total_results, 1)*100:.1f}%")

    # LLM 포맷 출력 (선택)
    if verbose:
        print(f"\n{'='*60}")
        print("LLM 입력 포맷 (일부)")
        print(f"{'='*60}")

        formatted = search_service.format_search_results_for_llm(search_results)
        # 처음 3000자만 출력
        print(formatted[:3000])
        if len(formatted) > 3000:
            print(f"\n... (총 {len(formatted)}자)")


async def main():
    """메인 함수."""
    parser = argparse.ArgumentParser(description="검색 및 크롤링 결과 테스트")
    parser.add_argument(
        "--cert",
        type=str,
        default="정보처리기사",
        help="테스트할 자격증 이름 (기본: 정보처리기사)",
    )
    parser.add_argument(
        "--no-crawl",
        action="store_true",
        help="크롤링 비활성화",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="상세 출력",
    )
    parser.add_argument(
        "--url",
        type=str,
        help="단일 URL 크롤링 테스트 (이 옵션 사용 시 검색 건너뜀)",
    )

    args = parser.parse_args()

    if args.url:
        # 단일 URL 크롤링 테스트
        await test_single_crawl(args.url)
    else:
        # 검색 및 크롤링 통합 테스트
        await test_search_with_crawl(
            certificate_title=args.cert,
            crawl_enabled=not args.no_crawl,
            verbose=args.verbose,
        )


if __name__ == "__main__":
    asyncio.run(main())
