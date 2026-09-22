#!/usr/bin/env python
r"""SearXNG 연결 및 검색 기능 테스트 스크립트.

SearXNG 실행법 (Windows PowerShell)
===================================

1. 설정 디렉토리 생성:
   mkdir -Force C:\Users\USER\Documents\searxng

2. settings.yml 파일 생성 (아래 내용):
   ---
   use_default_settings: true

   search:
     formats:
       - html
       - json

   server:
     limiter: false
     image_proxy: false
     secret_key: "my-super-secret-key-12345678901234567890"

   general:
     instance_name: "SearXNG Local"
   ---

3. 기존 컨테이너 삭제 후 실행:
   docker stop searxng
   docker rm searxng

   docker run -d -p 8888:8080 `
       -v "C:\Users\USER\Documents\searxng:/etc/searxng" `
       --name searxng `
       searxng/searxng

사용법:
    uv run python -m scripts.test_searxng
    uv run python -m scripts.test_searxng --url http://localhost:8888
    uv run python -m scripts.test_searxng --query "정보처리기사"
"""
import argparse
import asyncio
import sys

import httpx


async def test_searxng_connection(base_url: str) -> bool:
    """SearXNG 서버 연결을 테스트합니다.

    Args:
        base_url: SearXNG 서버 URL

    Returns:
        연결 성공 여부
    """
    print(f"\n{'='*60}")
    print("[1] SearXNG 서버 연결 테스트")
    print(f"{'='*60}")
    print(f"URL: {base_url}")

    try:
        async with httpx.AsyncClient() as client:
            # 1. 기본 연결 테스트
            response = await client.get(base_url, timeout=10.0)
            print(f"  상태 코드: {response.status_code}")
            headers_str = (
                str(dict(response.headers))[:200] if response.headers else "None"
            )
            print(f"  응답 헤더: {headers_str}...")

            if response.status_code == 200:
                print("  [OK] 서버 연결 성공")
                return True
            else:
                print(f"  [FAIL] 서버 응답 오류: {response.status_code}")
                return False

    except httpx.ConnectError as e:
        print(f"  [FAIL] 연결 실패: {e}")
        print("  -> SearXNG 서버가 실행 중인지 확인하세요:")
        print("     docker run -d -p 8888:8080 searxng/searxng")
        return False
    except Exception as e:
        print(f"  [FAIL] 예외 발생: {type(e).__name__}: {e}")
        return False


async def test_searxng_search_html(base_url: str, query: str) -> bool:
    """HTML 형식 검색을 테스트합니다.

    Args:
        base_url: SearXNG 서버 URL
        query: 검색어

    Returns:
        검색 성공 여부
    """
    print(f"\n{'='*60}")
    print("[2] HTML 검색 테스트 (format 없음)")
    print(f"{'='*60}")

    params = {
        "q": query,
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/search",
                params=params,
                timeout=30.0,
            )
            print(f"  URL: {response.url}")
            print(f"  상태 코드: {response.status_code}")

            if response.status_code == 200:
                print(f"  응답 길이: {len(response.text)} bytes")
                print("  [OK] HTML 검색 성공")
                return True
            else:
                print(f"  [FAIL] 검색 실패: {response.status_code}")
                print(f"  응답: {response.text[:500]}")
                return False

    except Exception as e:
        print(f"  [FAIL] 예외 발생: {type(e).__name__}: {e}")
        return False


async def test_searxng_search_json(base_url: str, query: str) -> bool:
    """JSON 형식 검색을 테스트합니다.

    Args:
        base_url: SearXNG 서버 URL
        query: 검색어

    Returns:
        검색 성공 여부
    """
    print(f"\n{'='*60}")
    print("[3] JSON 검색 테스트 (format=json)")
    print(f"{'='*60}")

    params = {
        "q": query,
        "format": "json",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/search",
                params=params,
                timeout=30.0,
            )
            print(f"  URL: {response.url}")
            print(f"  상태 코드: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"  결과 수: {len(results)}")
                if results:
                    print("  첫 번째 결과:")
                    print(f"    - 제목: {results[0].get('title', 'N/A')}")
                    print(f"    - URL: {results[0].get('url', 'N/A')}")
                print("  [OK] JSON 검색 성공")
                return True
            elif response.status_code == 403:
                print("  [FAIL] 403 Forbidden - JSON API 접근 차단됨")
                print("  -> SearXNG 설정에서 JSON API를 활성화해야 합니다.")
                print("  -> settings.yml에서 다음 설정 확인:")
                print("     search:")
                print("       formats:")
                print("         - html")
                print("         - json")
                return False
            else:
                print(f"  [FAIL] 검색 실패: {response.status_code}")
                print(f"  응답: {response.text[:500]}")
                return False

    except Exception as e:
        print(f"  [FAIL] 예외 발생: {type(e).__name__}: {e}")
        return False


async def test_searxng_search_json_with_headers(base_url: str, query: str) -> bool:
    """User-Agent 헤더를 포함한 JSON 검색을 테스트합니다.

    Args:
        base_url: SearXNG 서버 URL
        query: 검색어

    Returns:
        검색 성공 여부
    """
    print(f"\n{'='*60}")
    print("[4] JSON 검색 테스트 (User-Agent 포함)")
    print(f"{'='*60}")

    params = {
        "q": query,
        "format": "json",
        "language": "ko-KR",
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/search",
                params=params,
                headers=headers,
                timeout=30.0,
            )
            print(f"  URL: {response.url}")
            print(f"  상태 코드: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                print(f"  결과 수: {len(results)}")
                print("  [OK] JSON 검색 성공 (헤더 포함)")
                return True
            elif response.status_code == 403:
                print("  [FAIL] 403 Forbidden - 헤더 추가로도 해결 안 됨")
                return False
            else:
                print(f"  [FAIL] 검색 실패: {response.status_code}")
                return False

    except Exception as e:
        print(f"  [FAIL] 예외 발생: {type(e).__name__}: {e}")
        return False


async def test_searxng_config(base_url: str) -> bool:
    """SearXNG 설정 정보를 조회합니다.

    Args:
        base_url: SearXNG 서버 URL

    Returns:
        조회 성공 여부
    """
    print(f"\n{'='*60}")
    print("[5] SearXNG 설정 조회 (/config)")
    print(f"{'='*60}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{base_url}/config",
                timeout=10.0,
            )
            print(f"  상태 코드: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"  버전: {data.get('version', 'N/A')}")
                print(f"  인스턴스 이름: {data.get('instance_name', 'N/A')}")

                # 지원 형식 확인
                categories = data.get("categories", [])
                print(f"  카테고리: {categories}")

                engines = data.get("engines", [])
                print(f"  활성 엔진 수: {len(engines)}")

                print("  [OK] 설정 조회 성공")
                return True
            else:
                print(f"  [FAIL] 설정 조회 실패: {response.status_code}")
                return False

    except Exception as e:
        print(f"  [FAIL] 예외 발생: {type(e).__name__}: {e}")
        return False


async def main():
    """메인 함수."""
    parser = argparse.ArgumentParser(description="SearXNG 연결 테스트")
    parser.add_argument(
        "--url",
        default="http://localhost:8888",
        help="SearXNG 서버 URL (기본: http://localhost:8888)",
    )
    parser.add_argument(
        "--query",
        default="정보처리기사 자격증",
        help="테스트 검색어 (기본: 정보처리기사 자격증)",
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    query = args.query

    print("\n" + "=" * 60)
    print("SearXNG 연결 테스트")
    print("=" * 60)
    print(f"서버 URL: {base_url}")
    print(f"검색어: {query}")

    results = {
        "connection": await test_searxng_connection(base_url),
        "html_search": await test_searxng_search_html(base_url, query),
        "json_search": await test_searxng_search_json(base_url, query),
        "json_with_headers": await test_searxng_search_json_with_headers(
            base_url, query
        ),
        "config": await test_searxng_config(base_url),
    }

    # 결과 요약
    print(f"\n{'='*60}")
    print("테스트 결과 요약")
    print(f"{'='*60}")

    all_passed = True
    for test_name, passed in results.items():
        status = "[OK]" if passed else "[FAIL]"
        print(f"  {status} {test_name}")
        if not passed:
            all_passed = False

    print()

    if not results["connection"]:
        print("[해결 방법]")
        print("  1. SearXNG 서버가 실행 중인지 확인:")
        print("     docker ps | grep searxng")
        print()
        print("  2. SearXNG 서버 시작:")
        print("     docker run -d -p 8888:8080 --name searxng searxng/searxng")
        print()

    elif not results["json_search"]:
        print("[해결 방법] JSON API 403 Forbidden 오류")
        print()
        print("  SearXNG 설정 파일에서 JSON 형식을 활성화해야 합니다.")
        print()
        print("  1. Docker 볼륨 마운트로 설정 파일 사용:")
        print("     docker run -d -p 8888:8080 \\")
        print("       -v ./searxng:/etc/searxng \\")
        print("       --name searxng searxng/searxng")
        print()
        print("  2. settings.yml 파일 생성/수정:")
        print("     ```yaml")
        print("     search:")
        print("       formats:")
        print("         - html")
        print("         - json")
        print("     server:")
        print("       limiter: false  # rate limiting 비활성화")
        print("     ```")
        print()
        print("  3. 또는 환경변수로 설정:")
        print("     docker run -d -p 8888:8080 \\")
        print("       -e SEARXNG_SETTINGS_PATH=/etc/searxng/settings.yml \\")
        print("       searxng/searxng")
        print()

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
