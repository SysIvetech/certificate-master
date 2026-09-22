"""Integration test for the Chroma inspection page."""

from fastapi.testclient import TestClient

from app.api.chroma import get_vector_store_service
from app.main import app


class FakeVectorStoreService:
    """Fake vector store for rendering tests."""

    def __init__(self):
        self.list_kwargs = None
        self.requested_ids = []

    def get_collection_stats(self) -> dict:
        return {
            "host": "fake-host",
            "port": 1234,
            "collection_name": "test-collection",
            "total_vectors": 2,
        }

    def list_vectors(
        self,
        limit: int,
        offset: int,
        include_embeddings: bool = False,
        where: dict = None,
    ):
        self.list_kwargs = {
            "limit": limit,
            "offset": offset,
            "include_embeddings": include_embeddings,
            "where": where,
        }
        return [
            {
                "id": "vec-1",
                "metadata": {"title": "정보처리기사", "categories": "국가기술자격"},
            },
            {
                "id": "vec-2",
                "metadata": {"title": "네트워크보안", "categories": "민간자격"},
            },
        ]

    def get_by_id(self, vector_id: str):
        self.requested_ids.append(vector_id)
        if vector_id == "vec-1":
            return {
                "id": "vec-1",
                "values": [0.1, 0.2],
                "metadata": {"title": "정보처리기사", "categories": "국가기술자격"},
            }
        if vector_id == "vec-2":
            return {
                "id": "vec-2",
                "values": [0.3, 0.4],
                "metadata": {"title": "네트워크보안", "categories": "민간자격"},
            }
        return None


def test_chroma_page_renders_vectors_and_details(client: TestClient):
    """The /chroma page should show list data and detail panel."""
    fake_service = FakeVectorStoreService()
    app.dependency_overrides[get_vector_store_service] = lambda: fake_service

    try:
        response = client.get("/chroma?limit=5&offset=10&id=vec-2")
    finally:
        app.dependency_overrides.pop(get_vector_store_service, None)

    assert response.status_code == 200
    body = response.text

    assert "ChromaDB Inspector" in body
    assert "vec-1" in body
    assert "정보처리기사" in body
    assert "vec-2" in body
    assert "네트워크보안" in body
    assert fake_service.list_kwargs == {
        "limit": 5,
        "offset": 10,
        "include_embeddings": False,
        "where": None,
    }
    assert fake_service.requested_ids[0] == "vec-2"


def test_chroma_delete_single_vector(client: TestClient):
    """DELETE /chroma/{id} should delete vector and reset DB data."""
    fake_service = FakeVectorStoreService()
    fake_service.deleted_with_reset_ids = []

    def delete_certificate_with_reset(cert_id: str):
        fake_service.deleted_with_reset_ids.append(cert_id)

    fake_service.delete_certificate_with_reset = delete_certificate_with_reset

    app.dependency_overrides[get_vector_store_service] = lambda: fake_service

    try:
        response = client.delete("/chroma/vec-1")
    finally:
        app.dependency_overrides.pop(get_vector_store_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["deleted_id"] == "vec-1"
    # 변경: delete_certificate_with_reset이 호출되어야 함
    assert "vec-1" in fake_service.deleted_with_reset_ids


def test_chroma_delete_batch_vectors(client: TestClient):
    """POST /chroma/delete should delete vectors and reset DB data."""
    fake_service = FakeVectorStoreService()
    fake_service.deleted_with_reset_ids = []
    fake_service.batch_reset_result = {"success": 2, "not_found_ids": [], "errors": []}

    def delete_certificates_batch_with_reset(cert_ids: list[str]) -> dict:
        fake_service.deleted_with_reset_ids.extend(cert_ids)
        return fake_service.batch_reset_result

    fake_service.delete_certificates_batch_with_reset = (
        delete_certificates_batch_with_reset
    )

    app.dependency_overrides[get_vector_store_service] = lambda: fake_service

    try:
        response = client.post("/chroma/delete", json={"ids": ["vec-1", "vec-2"]})
    finally:
        app.dependency_overrides.pop(get_vector_store_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["deleted_count"] == 2
    # 변경: delete_certificates_batch_with_reset이 호출되어야 함
    assert "vec-1" in fake_service.deleted_with_reset_ids
    assert "vec-2" in fake_service.deleted_with_reset_ids
    # 새 응답 필드: reset_result
    assert "reset_result" in data


def test_chroma_page_has_delete_button(client: TestClient):
    """The /chroma page should have delete button when vector is selected."""
    fake_service = FakeVectorStoreService()
    app.dependency_overrides[get_vector_store_service] = lambda: fake_service

    try:
        response = client.get("/chroma?id=vec-1")
    finally:
        app.dependency_overrides.pop(get_vector_store_service, None)

    assert response.status_code == 200
    body = response.text
    assert "delete-btn" in body or "삭제" in body or "Delete" in body
