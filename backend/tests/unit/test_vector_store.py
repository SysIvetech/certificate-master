"""Unit tests for VectorStoreService (ChromaDB).

TDD: RED phase - Writing tests first.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestVectorStoreService:
    """Tests for VectorStoreService with ChromaDB."""

    def test_init_from_settings(self):
        """Test service initialization from settings."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                mock_chromadb.HttpClient.assert_called_once_with(
                    host="test-host", port=8000
                )
                mock_client.get_or_create_collection.assert_called_once()
                assert service.NAMESPACE == "certificates"

    def test_upsert_certificate_success(self):
        """Test upserting a single certificate embedding."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                cert_id = "cert-123"
                embedding = [0.1] * 1024
                metadata = {
                    "title": "정보처리기사",
                    "category": "국가기술자격",
                    "difficulty": 3,
                }

                service.upsert_certificate(cert_id, embedding, metadata)

                mock_collection.upsert.assert_called_once_with(
                    ids=[cert_id], embeddings=[embedding], metadatas=[metadata]
                )

    def test_upsert_certificates_batch(self):
        """Test batch upserting multiple certificates."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                vectors = [
                    ("cert-1", [0.1] * 1024, {"title": "자격증1"}),
                    ("cert-2", [0.2] * 1024, {"title": "자격증2"}),
                    ("cert-3", [0.3] * 1024, {"title": "자격증3"}),
                ]

                service.upsert_certificates_batch(vectors)

                mock_collection.upsert.assert_called_once_with(
                    ids=["cert-1", "cert-2", "cert-3"],
                    embeddings=[[0.1] * 1024, [0.2] * 1024, [0.3] * 1024],
                    metadatas=[
                        {"title": "자격증1"},
                        {"title": "자격증2"},
                        {"title": "자격증3"},
                    ],
                )

    def test_query_similar_basic(self):
        """Test querying similar certificates."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                # Mock query response
                mock_collection.query.return_value = {
                    "ids": [["cert-1", "cert-2"]],
                    "distances": [[0.05, 0.12]],
                    "metadatas": [
                        [{"title": "정보처리기사"}, {"title": "리눅스마스터"}]
                    ],
                }

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                query_embedding = [0.15] * 1024
                results = service.query_similar(query_embedding, top_k=10)

                # Verify query was called correctly
                mock_collection.query.assert_called_once_with(
                    query_embeddings=[query_embedding], n_results=10, where=None
                )

                # Verify results (distance -> score 변환: 1 - distance)
                assert len(results) == 2
                assert results[0]["id"] == "cert-1"
                assert results[0]["score"] == 0.95  # 1 - 0.05
                assert results[0]["metadata"]["title"] == "정보처리기사"
                assert results[1]["id"] == "cert-2"
                assert results[1]["score"] == 0.88  # 1 - 0.12

    def test_query_similar_with_filter(self):
        """Test querying similar certificates with filter."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                mock_collection.query.return_value = {
                    "ids": [[]],
                    "distances": [[]],
                    "metadatas": [[]],
                }

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                query_embedding = [0.15] * 1024
                filter_dict = {"difficulty": {"$lte": 3}}

                service.query_similar(query_embedding, top_k=5, filter_dict=filter_dict)

                # Verify filter was passed correctly
                mock_collection.query.assert_called_once_with(
                    query_embeddings=[query_embedding], n_results=5, where=filter_dict
                )

    def test_query_similar_empty_results(self):
        """Test querying when no similar certificates found."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                mock_collection.query.return_value = {
                    "ids": [[]],
                    "distances": [[]],
                    "metadatas": [[]],
                }

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                query_embedding = [0.15] * 1024
                results = service.query_similar(query_embedding)

                assert results == []

    def test_get_by_id_success(self):
        """Test retrieving certificate by ID."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                # Mock get response
                mock_collection.get.return_value = {
                    "ids": ["cert-123"],
                    "embeddings": [[0.1] * 1024],
                    "metadatas": [{"title": "정보처리기사"}],
                }

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                result = service.get_by_id("cert-123")

                mock_collection.get.assert_called_once_with(
                    ids=["cert-123"], include=["embeddings", "metadatas"]
                )
                assert result is not None
                assert result["id"] == "cert-123"
                assert result["metadata"]["title"] == "정보처리기사"

    def test_get_by_id_not_found(self):
        """Test retrieving non-existent certificate."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                mock_collection.get.return_value = {
                    "ids": [],
                    "embeddings": [],
                    "metadatas": [],
                }

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                result = service.get_by_id("nonexistent")

                assert result is None

    def test_get_by_id_with_numpy_embeddings(self):
        """Ensure numpy embeddings do not raise truthiness errors."""
        try:
            import numpy as np
        except ImportError:
            pytest.skip("numpy not installed")

        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                mock_collection.get.return_value = {
                    "ids": ["cert-999"],
                    "embeddings": np.array([[0.1, 0.2]]),
                    "metadatas": [{"title": "정보처리기사"}],
                }

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                result = service.get_by_id("cert-999")

                assert result is not None
                assert result["values"] == [0.1, 0.2]
                assert result["metadata"]["title"] == "정보처리기사"

    def test_list_vectors_metadata_only(self):
        """Test listing vectors without embeddings for dashboard view."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                mock_collection.get.return_value = {
                    "ids": ["cert-1", "cert-2"],
                    "metadatas": [
                        {"title": "정보처리기사", "category": "국가기술자격"},
                        {"title": "네트워크관리사", "category": "국가공인"},
                    ],
                    "embeddings": None,
                }

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                results = service.list_vectors(
                    limit=2, offset=1, include_embeddings=False
                )

                mock_collection.get.assert_called_once_with(
                    ids=None,
                    where=None,
                    include=["metadatas"],
                    limit=2,
                    offset=1,
                )
                assert len(results) == 2
                assert results[0]["id"] == "cert-1"
                assert results[0]["metadata"]["title"] == "정보처리기사"
                assert "values" not in results[0]

    def test_list_vectors_with_embeddings(self):
        """Test listing vectors with embeddings when explicitly requested."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                mock_collection.get.return_value = {
                    "ids": ["cert-1"],
                    "metadatas": [{"title": "정보보안기사"}],
                    "embeddings": [[0.1, 0.2, 0.3]],
                }

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                results = service.list_vectors(
                    limit=1, offset=0, include_embeddings=True
                )

                mock_collection.get.assert_called_once_with(
                    ids=None,
                    where=None,
                    include=["metadatas", "embeddings"],
                    limit=1,
                    offset=0,
                )
                assert results[0]["values"] == [0.1, 0.2, 0.3]

    def test_get_collection_stats(self):
        """Test retrieving collection statistics for dashboard header."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_collection.count.return_value = 42
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                stats = service.get_collection_stats()

                mock_collection.count.assert_called_once()
                assert stats["collection_name"] == "test-collection"
                assert stats["total_vectors"] == 42
                assert stats["host"] == "test-host"
                assert stats["port"] == 8000

    def test_delete_certificate_success(self):
        """Test deleting a certificate."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                service.delete_certificate("cert-123")

                mock_collection.delete.assert_called_once_with(ids=["cert-123"])

    def test_delete_certificates_batch(self):
        """Test batch deleting certificates."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                cert_ids = ["cert-1", "cert-2", "cert-3"]
                service.delete_certificates_batch(cert_ids)

                mock_collection.delete.assert_called_once_with(ids=cert_ids)


class TestVectorStoreServiceSearchRecords:
    """Tests for text-based search with EmbeddingService integration."""

    def test_search_records_with_text(self):
        """Test text-based search using EmbeddingService."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                mock_collection.query.return_value = {
                    "ids": [["cert-1"]],
                    "distances": [[0.1]],
                    "metadatas": [[{"title": "정보처리기사"}]],
                }

                with patch(
                    "app.services.embedding.vector_store.EmbeddingService"
                ) as mock_embed:
                    mock_embed_instance = MagicMock()
                    mock_embed.return_value = mock_embed_instance
                    mock_embed_instance.create_embedding.return_value = [0.1] * 1024

                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    results = service.search_records(
                        namespace="certificates", query="IT 자격증", top_k=5
                    )

                    # EmbeddingService가 호출되어야 함
                    mock_embed_instance.create_embedding.assert_called_once_with(
                        "IT 자격증"
                    )
                    assert len(results) == 1
                    assert results[0]["id"] == "cert-1"


class TestVectorStoreServiceFormatRecord:
    """Tests for format_record_for_upsert method."""

    def test_format_record_for_upsert_basic(self):
        """Test formatting a certificate for upsert."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                cert = {
                    "id": "cert-123",
                    "title": "정보처리기사",
                    "categories": [{"code": "T", "name": "국가기술자격"}],
                    "series": "정보처리",
                    "overview": "IT 분야의 대표 자격증",
                    "difficulty": 3,
                    "study_period_days": 90,
                    "career_info": {
                        "industry": ["IT", "소프트웨어"],
                        "average_salary": "연 4,000만원",
                    },
                    "exam_info": {"exam_type": "필기+실기"},
                }

                record = service.format_record_for_upsert(cert)

                assert record["_id"] == "cert-123"
                assert "chunk_text" in record
                assert "정보처리기사" in record["chunk_text"]
                assert record["title"] == "정보처리기사"
                assert record["categories"] == "국가기술자격"


class TestVectorStoreUpsertVerification:
    """ChromaDB 업로드 후 검증 테스트."""

    def test_upsert_certificates_batch_integrated_returns_result(self):
        """upsert_certificates_batch_integrated가 결과를 반환하는지 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_collection.upsert.return_value = None
                mock_collection.get.return_value = {
                    "ids": ["test-id-1"],
                    "embeddings": [[0.1] * 1024],
                    "metadatas": [{"title": "Test"}],
                }
                mock_client.get_or_create_collection.return_value = mock_collection

                with patch(
                    "app.services.embedding.vector_store.EmbeddingService"
                ) as mock_embed:
                    mock_embed_instance = MagicMock()
                    mock_embed.return_value = mock_embed_instance
                    mock_embed_instance.create_embeddings_batch.return_value = [
                        [0.1] * 1024
                    ]

                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    test_certs = [
                        {
                            "id": "test-id-1",
                            "title": "테스트 자격증",
                            "category": "국가기술자격",
                            "series": "IT",
                            "overview": "테스트 개요",
                            "difficulty": 3,
                            "study_period_days": 90,
                            "career_info": {},
                            "exam_info": {},
                            "user_reviews": {},
                            "study_guide": {},
                        }
                    ]

                    # 결과를 반환해야 함
                    result = service.upsert_certificates_batch_integrated(test_certs)

                    # 결과가 dict여야 함
                    assert isinstance(result, dict)
                    # 업로드된 개수
                    assert "uploaded_count" in result
                    assert result["uploaded_count"] == 1
                    # 검증된 개수
                    assert "verified_count" in result
                    assert result["verified_count"] == 1

    def test_upsert_certificates_batch_integrated_verifies_upload(self):
        """업로드 후 실제로 ChromaDB에 저장되었는지 검증하는지 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_collection.upsert.return_value = None
                mock_collection.get.return_value = {
                    "ids": ["test-id-1", "test-id-2"],
                    "embeddings": [[0.1] * 1024, [0.2] * 1024],
                    "metadatas": [{"title": "Test1"}, {"title": "Test2"}],
                }
                mock_client.get_or_create_collection.return_value = mock_collection

                with patch(
                    "app.services.embedding.vector_store.EmbeddingService"
                ) as mock_embed:
                    mock_embed_instance = MagicMock()
                    mock_embed.return_value = mock_embed_instance
                    mock_embed_instance.create_embeddings_batch.return_value = [
                        [0.1] * 1024,
                        [0.2] * 1024,
                    ]

                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    test_certs = [
                        {
                            "id": "test-id-1",
                            "title": "자격증1",
                            "category": "국가",
                            "series": "",
                            "overview": "",
                            "difficulty": None,
                            "study_period_days": None,
                            "career_info": {},
                            "exam_info": {},
                            "user_reviews": {},
                            "study_guide": {},
                        },
                        {
                            "id": "test-id-2",
                            "title": "자격증2",
                            "category": "국가",
                            "series": "",
                            "overview": "",
                            "difficulty": None,
                            "study_period_days": None,
                            "career_info": {},
                            "exam_info": {},
                            "user_reviews": {},
                            "study_guide": {},
                        },
                    ]

                    result = service.upsert_certificates_batch_integrated(test_certs)

                    # upsert 후 get이 호출되어야 함 (검증)
                    mock_collection.get.assert_called()
                    # 2개 모두 검증됨
                    assert result["verified_count"] == 2

    def test_upsert_certificates_batch_integrated_handles_partial_upload(self):
        """일부만 업로드된 경우 처리 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_collection.upsert.return_value = None
                mock_collection.get.return_value = {
                    "ids": ["test-id-1"],  # 1개만 저장됨
                    "embeddings": [[0.1] * 1024],
                    "metadatas": [{"title": "Test1"}],
                }
                mock_client.get_or_create_collection.return_value = mock_collection

                with patch(
                    "app.services.embedding.vector_store.EmbeddingService"
                ) as mock_embed:
                    mock_embed_instance = MagicMock()
                    mock_embed.return_value = mock_embed_instance
                    mock_embed_instance.create_embeddings_batch.return_value = [
                        [0.1] * 1024,
                        [0.2] * 1024,
                    ]

                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    test_certs = [
                        {
                            "id": "test-id-1",
                            "title": "자격증1",
                            "category": "국가",
                            "series": "",
                            "overview": "",
                            "difficulty": None,
                            "study_period_days": None,
                            "career_info": {},
                            "exam_info": {},
                            "user_reviews": {},
                            "study_guide": {},
                        },
                        {
                            "id": "test-id-2",
                            "title": "자격증2",
                            "category": "국가",
                            "series": "",
                            "overview": "",
                            "difficulty": None,
                            "study_period_days": None,
                            "career_info": {},
                            "exam_info": {},
                            "user_reviews": {},
                            "study_guide": {},
                        },
                    ]

                    result = service.upsert_certificates_batch_integrated(test_certs)

                    # 2개 업로드 시도, 1개만 검증됨
                    assert result["uploaded_count"] == 2
                    assert result["verified_count"] == 1
                    # 실패한 ID 목록
                    assert "failed_ids" in result
                    assert "test-id-2" in result["failed_ids"]

    def test_upsert_certificates_batch_integrated_raises_on_connection_error(self):
        """ChromaDB 연결 실패 시 예외 발생 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_collection.upsert.side_effect = Exception("Connection refused")
                mock_client.get_or_create_collection.return_value = mock_collection

                with patch(
                    "app.services.embedding.vector_store.EmbeddingService"
                ) as mock_embed:
                    mock_embed_instance = MagicMock()
                    mock_embed.return_value = mock_embed_instance
                    mock_embed_instance.create_embeddings_batch.return_value = [
                        [0.1] * 1024
                    ]

                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    test_certs = [
                        {
                            "id": "test-id-1",
                            "title": "자격증1",
                            "category": "국가",
                            "series": "",
                            "overview": "",
                            "difficulty": None,
                            "study_period_days": None,
                            "career_info": {},
                            "exam_info": {},
                            "user_reviews": {},
                            "study_guide": {},
                        }
                    ]

                    # 예외가 발생해야 함
                    with pytest.raises(Exception) as exc_info:
                        service.upsert_certificates_batch_integrated(test_certs)

                    assert "Connection refused" in str(exc_info.value)


class TestVectorStoreDuplicateCheck:
    """중복 체크 로직 테스트."""

    def test_check_existing_vectors_returns_existing_ids(self):
        """ChromaDB에 이미 존재하는 ID를 반환하는지 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                # id-1, id-3는 존재, id-2는 없음
                mock_collection.get.return_value = {
                    "ids": ["id-1", "id-3"],
                    "embeddings": None,
                    "metadatas": None,
                }
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                ids_to_check = ["id-1", "id-2", "id-3"]
                existing_ids = service.check_existing_vectors(ids_to_check)

                mock_collection.get.assert_called_once_with(ids=ids_to_check)
                assert set(existing_ids) == {"id-1", "id-3"}

    def test_check_existing_vectors_empty_result(self):
        """ChromaDB에 아무것도 없을 때 빈 리스트 반환 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_collection.get.return_value = {
                    "ids": [],
                    "embeddings": None,
                    "metadatas": None,
                }
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                existing_ids = service.check_existing_vectors(["id-1", "id-2"])

                assert existing_ids == []

    def test_upsert_with_skip_existing_skips_duplicates(self):
        """이미 존재하는 벡터는 스킵하는지 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()

                # check_existing_vectors: id-1은 이미 존재
                def mock_get(ids=None, **kwargs):
                    if ids == ["id-1", "id-2"]:
                        return {"ids": ["id-1"], "embeddings": None, "metadatas": None}
                    elif ids == ["id-2"]:  # 검증용
                        return {
                            "ids": ["id-2"],
                            "embeddings": [[0.1] * 1024],
                            "metadatas": [{}],
                        }
                    return {"ids": [], "embeddings": None, "metadatas": None}

                mock_collection.get.side_effect = mock_get
                mock_collection.upsert.return_value = None
                mock_client.get_or_create_collection.return_value = mock_collection

                with patch(
                    "app.services.embedding.vector_store.EmbeddingService"
                ) as mock_embed:
                    mock_embed_instance = MagicMock()
                    mock_embed.return_value = mock_embed_instance
                    # id-2만 임베딩 생성 (1개)
                    mock_embed_instance.create_embeddings_batch.return_value = [
                        [0.1] * 1024
                    ]

                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    test_certs = [
                        {
                            "id": "id-1",
                            "title": "자격증1",
                            "category": "국가",
                            "series": "",
                            "overview": "",
                            "difficulty": None,
                            "study_period_days": None,
                            "career_info": {},
                            "exam_info": {},
                            "user_reviews": {},
                            "study_guide": {},
                        },
                        {
                            "id": "id-2",
                            "title": "자격증2",
                            "category": "국가",
                            "series": "",
                            "overview": "",
                            "difficulty": None,
                            "study_period_days": None,
                            "career_info": {},
                            "exam_info": {},
                            "user_reviews": {},
                            "study_guide": {},
                        },
                    ]

                    result = service.upsert_certificates_batch_integrated(
                        test_certs, skip_existing=True
                    )

                    # id-1은 스킵, id-2만 업로드
                    assert result["skipped_count"] == 1
                    assert result["uploaded_count"] == 1


class TestVectorStoreConnectionRetry:
    """B2: ChromaDB 연결 재시도 로직 테스트."""

    def test_init_retries_on_connection_failure(self):
        """연결 실패 시 재시도하는지 테스트.

        B2 Critical Issue: ChromaDB 서버가 일시적으로 다운되었을 때
        재시도 로직이 동작해야 합니다.
        """
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                # heartbeat가 처음 2번 실패, 3번째 성공
                mock_client.heartbeat.side_effect = [
                    Exception("Connection refused"),
                    Exception("Connection refused"),
                    1234567890,  # 성공 (timestamp)
                ]

                with patch("app.services.embedding.vector_store.time") as mock_time:
                    mock_time.sleep = MagicMock()

                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    # heartbeat가 3번 호출되어야 함
                    assert mock_client.heartbeat.call_count == 3
                    # 재시도 간격 sleep이 2번 호출되어야 함
                    assert mock_time.sleep.call_count == 2
                    # 서비스가 정상적으로 생성되어야 함
                    assert service is not None

    def test_init_raises_connection_error_after_max_retries(self):
        """최대 재시도 횟수 초과 시 ConnectionError 발생 테스트.

        B2 Critical Issue: 재시도 횟수 초과 시 명확한 에러 메시지와 함께
        ConnectionError를 발생시켜야 합니다.
        """
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client

                # heartbeat가 항상 실패
                mock_client.heartbeat.side_effect = Exception("Connection refused")

                with patch("app.services.embedding.vector_store.time") as mock_time:
                    mock_time.sleep = MagicMock()

                    from app.services.vector_store import VectorStoreService

                    # ConnectionError가 발생해야 함
                    with pytest.raises(ConnectionError) as exc_info:
                        VectorStoreService()

                    assert "ChromaDB" in str(exc_info.value)

    def test_init_uses_exponential_backoff(self):
        """지수 백오프 재시도 전략 테스트.

        재시도 간격이 지수적으로 증가해야 합니다 (1초, 2초, 4초...).
        """
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                # heartbeat가 2번 실패 후 성공
                mock_client.heartbeat.side_effect = [
                    Exception("Connection refused"),
                    Exception("Timeout"),
                    1234567890,
                ]

                with patch("app.services.embedding.vector_store.time") as mock_time:
                    sleep_calls = []
                    mock_time.sleep = lambda x: sleep_calls.append(x)

                    from app.services.vector_store import VectorStoreService

                    VectorStoreService()

                    # 지수 백오프: 첫 번째 재시도 1초, 두 번째 재시도 2초
                    assert sleep_calls[0] == 1  # 2^0
                    assert sleep_calls[1] == 2  # 2^1


class TestVectorStorePartialFailure:
    """Phase 3: 부분 실패 시나리오 테스트."""

    def test_upsert_batch_handles_partial_embedding_failure(self):
        """배치 임베딩 생성 중 일부 실패 처리 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection
                mock_client.heartbeat.return_value = 1234567890

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                # Mock embedding service - 예외 발생
                mock_embedding = MagicMock()
                mock_embedding.create_embeddings_batch.side_effect = Exception(
                    "Embedding generation failed"
                )
                service.embedding_service = mock_embedding

                records = [
                    {"id": "cert-1", "chunk_text": "텍스트1", "title": "자격증1"},
                    {"id": "cert-2", "chunk_text": "텍스트2", "title": "자격증2"},
                ]

                # 예외가 발생해야 함 (KeyError 또는 Embedding 에러)
                with pytest.raises(Exception):
                    service.upsert_certificates_batch_integrated(
                        records, skip_existing=False
                    )

    def test_search_handles_none_metadata(self):
        """검색 결과 중 메타데이터가 None인 경우 처리 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection
                mock_client.heartbeat.return_value = 1234567890

                # 일부 결과의 메타데이터가 None인 경우
                mock_collection.query.return_value = {
                    "ids": [["cert-1", "cert-2"]],
                    "distances": [[0.1, 0.2]],
                    "metadatas": [[{"title": "자격증1"}, None]],  # 일부 None
                    "documents": [["텍스트1", "텍스트2"]],
                }

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                results = service.query_similar(query_embedding=[0.1] * 1024, top_k=5)

                # None 메타데이터도 빈 딕셔너리로 처리
                assert len(results) == 2
                assert results[0]["metadata"] == {"title": "자격증1"}
                assert results[1]["metadata"] == {} or results[1]["metadata"] is None


class TestVectorStoreSyncOrphanedVectorIds:
    """vector_id 없는 자격증의 ChromaDB 존재 여부 확인 및 동기화 테스트."""

    def test_find_certs_existing_in_chroma_without_vector_id(self):
        """MariaDB에 vector_id 없지만 ChromaDB에 존재하는 자격증 찾기 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()

                # cert-1, cert-2는 ChromaDB에 존재, cert-3는 없음
                mock_collection.get.return_value = {
                    "ids": ["cert-1", "cert-2"],
                    "embeddings": None,
                    "metadatas": None,
                }
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                # vector_id가 없는 자격증 ID 목록
                cert_ids_without_vector_id = ["cert-1", "cert-2", "cert-3"]

                # ChromaDB에 이미 존재하는 ID 확인
                existing_ids = service.check_existing_vectors(
                    cert_ids_without_vector_id
                )

                # cert-1, cert-2는 ChromaDB에 있음
                assert set(existing_ids) == {"cert-1", "cert-2"}
                # cert-3는 ChromaDB에 없음 → 새로 생성 필요
                missing_ids = set(cert_ids_without_vector_id) - set(existing_ids)
                assert missing_ids == {"cert-3"}

    def test_sync_vector_ids_for_existing_chroma_records(self):
        """ChromaDB에 존재하는 자격증의 vector_id를 MariaDB에 동기화하는 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                with patch(
                    "app.services.embedding.vector_store._get_db_session"
                ) as mock_get_session:
                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # 자격증이 DB에 존재하는 것처럼 설정
                    mock_cert1 = MagicMock()
                    mock_cert1.vector_id = None
                    mock_cert2 = MagicMock()
                    mock_cert2.vector_id = None

                    def mock_filter_first(cert_id):
                        mock_query = MagicMock()
                        if cert_id == "cert-1":
                            mock_query.first.return_value = mock_cert1
                        elif cert_id == "cert-2":
                            mock_query.first.return_value = mock_cert2
                        else:
                            mock_query.first.return_value = None
                        return mock_query

                    mock_filter = MagicMock()
                    mock_filter.filter.side_effect = lambda x: mock_filter_first(
                        str(x.right.value) if hasattr(x.right, "value") else "unknown"
                    )
                    mock_session.query.return_value = mock_filter

                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    # ChromaDB에 존재하는 ID로 동기화
                    mappings = [("cert-1", "cert-1"), ("cert-2", "cert-2")]
                    service.sync_vector_ids_to_db_batch(mappings)

                    # 커밋이 호출되어야 함
                    mock_session.commit.assert_called_once()

    def test_reconcile_certs_without_vector_id(self):
        """vector_id 없는 자격증에 대해 ChromaDB 조회 후 동기화/생성 분리 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()

                # cert-1은 ChromaDB에 이미 존재, cert-2는 없음
                mock_collection.get.return_value = {
                    "ids": ["cert-1"],
                    "embeddings": None,
                    "metadatas": None,
                }
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                # vector_id가 없는 자격증 목록 (실제 시나리오)
                certs_without_vector_id = [
                    {"id": "cert-1", "title": "정보처리기사", "vector_id": None},
                    {"id": "cert-2", "title": "리눅스마스터", "vector_id": None},
                ]

                cert_ids = [c["id"] for c in certs_without_vector_id]
                existing_in_chroma = set(service.check_existing_vectors(cert_ids))

                # 동기화만 필요한 자격증 (ChromaDB에 이미 있음)
                certs_to_sync_only = [
                    c for c in certs_without_vector_id if c["id"] in existing_in_chroma
                ]

                # 새로 생성이 필요한 자격증 (ChromaDB에 없음)
                certs_to_create = [
                    c
                    for c in certs_without_vector_id
                    if c["id"] not in existing_in_chroma
                ]

                # cert-1은 동기화만 필요
                assert len(certs_to_sync_only) == 1
                assert certs_to_sync_only[0]["id"] == "cert-1"

                # cert-2는 새로 생성 필요
                assert len(certs_to_create) == 1
                assert certs_to_create[0]["id"] == "cert-2"
