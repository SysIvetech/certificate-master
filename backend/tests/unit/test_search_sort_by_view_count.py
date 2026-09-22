"""검색 정렬 기능 테스트 - 기본 정렬이 view_count 내림차순인지 확인.

TDD Red Phase: 기본 검색 정렬이 조회수 내림차순으로 동작하는지 검증.
"""

from fastapi.testclient import TestClient


class TestSearchSortByViewCount:
    """검색 결과의 기본 정렬이 view_count 내림차순인지 테스트."""

    def test_default_sort_is_view_count_descending(
        self,
        client: TestClient,
        test_supabase_client,
        clean_test_certificates,
    ):
        """기본 검색 시 view_count 내림차순으로 정렬되는지 확인.

        Given: view_count가 다른 테스트 자격증 3개가 존재
        When: GET /api/v1/certificates/search (sort_by 파라미터 없이)
        Then: view_count가 높은 순서대로 반환되어야 함
        """
        # 테스트 자격증 3개 생성 (view_count 다르게)
        certs_data = [
            {
                "categories": [{"code": "T", "name": "국가기술자격"}],
                "series": "정렬테스트",
                "title": "정렬테스트_A자격증",
                "raw_id": "TEST_sort_a",
                "view_count": 10,
            },
            {
                "categories": [{"code": "T", "name": "국가기술자격"}],
                "series": "정렬테스트",
                "title": "정렬테스트_B자격증",
                "raw_id": "TEST_sort_b",
                "view_count": 100,
            },
            {
                "categories": [{"code": "T", "name": "국가기술자격"}],
                "series": "정렬테스트",
                "title": "정렬테스트_C자격증",
                "raw_id": "TEST_sort_c",
                "view_count": 50,
            },
        ]

        for cert in certs_data:
            test_supabase_client.table("certificates").insert(cert).execute()

        # 검색 (기본 정렬)
        response = client.get("/api/v1/certificates/search?q=정렬테스트&page_size=100")
        assert response.status_code == 200

        data = response.json()
        items = data["items"]

        # 테스트 자격증만 필터
        test_items = [i for i in items if i["raw_id"].startswith("TEST_sort_")]
        assert len(test_items) == 3

        # view_count 내림차순 확인: B(100) > C(50) > A(10)
        view_counts = [i["view_count"] for i in test_items]
        assert view_counts == sorted(view_counts, reverse=True), (
            f"기본 정렬이 view_count 내림차순이어야 합니다. " f"실제: {view_counts}"
        )

    def test_sort_by_view_count_explicit(
        self,
        client: TestClient,
        test_supabase_client,
        clean_test_certificates,
    ):
        """sort_by=view_count 파라미터로 명시적 정렬 확인.

        Given: view_count가 다른 테스트 자격증이 존재
        When: GET /api/v1/certificates/search?sort_by=view_count
        Then: view_count가 높은 순서대로 반환
        """
        certs_data = [
            {
                "categories": [{"code": "T", "name": "국가기술자격"}],
                "series": "명시정렬",
                "title": "명시정렬_낮음",
                "raw_id": "TEST_explicit_low",
                "view_count": 5,
            },
            {
                "categories": [{"code": "T", "name": "국가기술자격"}],
                "series": "명시정렬",
                "title": "명시정렬_높음",
                "raw_id": "TEST_explicit_high",
                "view_count": 500,
            },
        ]

        for cert in certs_data:
            test_supabase_client.table("certificates").insert(cert).execute()

        response = client.get(
            "/api/v1/certificates/search?q=명시정렬&sort_by=view_count&page_size=100"
        )
        assert response.status_code == 200

        items = response.json()["items"]
        test_items = [i for i in items if i["raw_id"].startswith("TEST_explicit_")]
        assert len(test_items) == 2

        # 높음(500) → 낮음(5) 순서
        assert test_items[0]["title"] == "명시정렬_높음"
        assert test_items[1]["title"] == "명시정렬_낮음"

    def test_sort_by_title(
        self,
        client: TestClient,
        test_supabase_client,
        clean_test_certificates,
    ):
        """sort_by=title 파라미터로 제목순 정렬 확인.

        Given: 자격증이 존재
        When: GET /api/v1/certificates/search?sort_by=title
        Then: 제목 오름차순으로 반환
        """
        certs_data = [
            {
                "categories": [{"code": "T", "name": "국가기술자격"}],
                "series": "제목정렬",
                "title": "제목정렬_다라마",
                "raw_id": "TEST_title_c",
                "view_count": 100,
            },
            {
                "categories": [{"code": "T", "name": "국가기술자격"}],
                "series": "제목정렬",
                "title": "제목정렬_가나다",
                "raw_id": "TEST_title_a",
                "view_count": 1,
            },
            {
                "categories": [{"code": "T", "name": "국가기술자격"}],
                "series": "제목정렬",
                "title": "제목정렬_바사아",
                "raw_id": "TEST_title_b",
                "view_count": 50,
            },
        ]

        for cert in certs_data:
            test_supabase_client.table("certificates").insert(cert).execute()

        response = client.get(
            "/api/v1/certificates/search?q=제목정렬&sort_by=title&page_size=100"
        )
        assert response.status_code == 200

        items = response.json()["items"]
        test_items = [i for i in items if i["raw_id"].startswith("TEST_title_")]
        assert len(test_items) == 3

        # 제목 오름차순: 가나다 → 다라마 → 바사아
        titles = [i["title"] for i in test_items]
        assert titles == sorted(
            titles
        ), f"sort_by=title은 제목 오름차순이어야 합니다. 실제: {titles}"
