"""ChromaDB 타이틀 검색 기능 테스트.

ChromaDB의 where 필터는 $contains를 지원하지 않으므로,
모든 벡터를 가져온 후 Python에서 타이틀 필터링을 수행합니다.
"""

from fastapi.testclient import TestClient

from app.api.chroma import get_vector_store_service
from app.main import app


class FakeVectorStoreServiceWithSearch:
    """검색 기능을 포함한 Fake vector store."""

    def __init__(self):
        self.list_called = False
        self.list_limit = None

    def get_collection_stats(self) -> dict:
        return {
            "host": "fake-host",
            "port": 1234,
            "collection_name": "test-collection",
            "total_vectors": 100,
        }

    def list_vectors(
        self,
        limit: int,
        offset: int,
        include_embeddings: bool = False,
        where: dict = None,
    ):
        """벡터 목록 조회."""
        self.list_called = True
        self.list_limit = limit
        # 전체 데이터 시뮬레이션 (검색용 큰 limit일 때)
        if limit >= 1000:
            return [
                {
                    "id": "vec-1",
                    "metadata": {"title": "정보처리기사", "category": "국가기술자격"},
                },
                {
                    "id": "vec-2",
                    "metadata": {"title": "네트워크관리사", "category": "민간자격"},
                },
                {
                    "id": "vec-food-1",
                    "metadata": {"title": "식육가공기사", "category": "국가기술자격"},
                },
                {
                    "id": "vec-food-2",
                    "metadata": {"title": "식육처리기능사", "category": "국가기술자격"},
                },
                {
                    "id": "vec-food-3",
                    "metadata": {"title": "식육가공기능사", "category": "국가기술자격"},
                },
            ]
        # 일반 페이지네이션
        return [
            {
                "id": "vec-1",
                "metadata": {"title": "정보처리기사", "category": "국가기술자격"},
            },
            {
                "id": "vec-2",
                "metadata": {"title": "네트워크관리사", "category": "민간자격"},
            },
        ]

    def get_by_id(self, vector_id: str):
        data = {
            "vec-food-1": {
                "id": "vec-food-1",
                "values": [0.1, 0.2],
                "metadata": {"title": "식육가공기사", "category": "국가기술자격"},
            },
            "vec-food-2": {
                "id": "vec-food-2",
                "values": [0.3, 0.4],
                "metadata": {"title": "식육처리기능사", "category": "국가기술자격"},
            },
            "vec-food-3": {
                "id": "vec-food-3",
                "values": [0.5, 0.6],
                "metadata": {"title": "식육가공기능사", "category": "국가기술자격"},
            },
        }
        return data.get(vector_id)


def test_chroma_page_search_filters_by_title_contains(client: TestClient):
    """검색어가 있을 때 타이틀에 검색어가 포함된 결과만 반환해야 합니다."""
    fake_service = FakeVectorStoreServiceWithSearch()
    app.dependency_overrides[get_vector_store_service] = lambda: fake_service

    try:
        response = client.get("/chroma?q=식육가공&limit=20")
    finally:
        app.dependency_overrides.pop(get_vector_store_service, None)

    assert response.status_code == 200
    body = response.text
    # "식육가공"이 포함된 자격증만 표시되어야 함
    assert "식육가공기사" in body
    assert "식육가공기능사" in body
    # "식육처리기능사"는 "식육가공"이 아니므로 제외되어야 함
    assert "식육처리기능사" not in body
    # 다른 자격증도 제외
    assert "정보처리기사" not in body


def test_chroma_page_without_search_uses_list_vectors(client: TestClient):
    """검색어가 없을 때는 일반 list_vectors를 사용해야 합니다."""
    fake_service = FakeVectorStoreServiceWithSearch()
    app.dependency_overrides[get_vector_store_service] = lambda: fake_service

    try:
        response = client.get("/chroma?limit=20")
    finally:
        app.dependency_overrides.pop(get_vector_store_service, None)

    assert response.status_code == 200
    # list_vectors가 호출되어야 함
    assert fake_service.list_called is True
    # 일반 limit으로 호출 (검색용 큰 limit 아님)
    assert fake_service.list_limit == 20
    body = response.text
    assert "정보처리기사" in body


def test_chroma_page_search_no_results(client: TestClient):
    """검색 결과가 없을 때 적절한 메시지를 표시해야 합니다."""
    fake_service = FakeVectorStoreServiceWithSearch()
    app.dependency_overrides[get_vector_store_service] = lambda: fake_service

    try:
        response = client.get("/chroma?q=없는자격증xyz")
    finally:
        app.dependency_overrides.pop(get_vector_store_service, None)

    assert response.status_code == 200
    body = response.text
    # 결과가 없을 때 메시지 표시
    assert "No vectors found" in body or "검색 결과 없음" in body
