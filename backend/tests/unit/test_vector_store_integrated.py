"""ChromaDB OpenAI 임베딩 통합 테스트.

TDD: RED phase - ChromaDB의 OpenAI 임베딩 기능 사용 테스트.
"""

from unittest.mock import MagicMock, patch


class TestVectorStoreServiceIntegrated:
    """ChromaDB + OpenAI 임베딩을 사용하는 VectorStoreService 테스트."""

    def test_search_records_with_text(self):
        """텍스트 기반 검색 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                # Mock search response
                mock_collection.query.return_value = {
                    "ids": [["cert-001", "cert-002"]],
                    "distances": [[0.05, 0.15]],
                    "metadatas": [
                        [
                            {"title": "정보처리기사", "category": "국가기술자격"},
                            {"title": "정보보안기사", "category": "국가기술자격"},
                        ]
                    ],
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
                        namespace="certificates", query="IT 개발자 자격증 추천", top_k=5
                    )

                    mock_embed_instance.create_embedding.assert_called_once()
                    assert len(results) == 2
                    assert results[0]["id"] == "cert-001"
                    assert results[0]["score"] == 0.95  # 1 - 0.05

    def test_format_record_for_upsert(self):
        """자격증 데이터를 upsert용 레코드로 포맷 테스트."""
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
                    "id": "uuid-123",
                    "title": "정보처리기사",
                    "categories": [{"code": "T", "name": "국가기술자격"}],
                    "series": "정보처리",
                    "overview": "IT 분야의 대표적인 자격증입니다.",
                    "difficulty": 3,
                    "study_period_days": 90,
                    "career_info": {"industry": ["IT", "소프트웨어"]},
                    "job_market_info": {},
                    "feasibility_info": {},
                }

                record = service.format_record_for_upsert(cert)

                assert record["_id"] == "uuid-123"
                assert "chunk_text" in record
                assert "정보처리기사" in record["chunk_text"]
                # Contextual Prefix에서 career_info.industry 기반으로 "IT" 포함
                assert "IT" in record["chunk_text"]
                assert record["title"] == "정보처리기사"
                assert record["categories"] == "국가기술자격"

    def test_format_record_with_career_info(self):
        """진로 정보가 포함된 자격증 포맷 테스트."""
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
                    "id": "uuid-456",
                    "title": "관세사",
                    "categories": [{"code": "S", "name": "국가전문자격"}],
                    "overview": "무역 전문 자격증",
                    "career_info": {
                        "industry": ["무역", "물류"],
                        "related_jobs": ["관세사", "무역전문가"],
                        "average_salary": "연 5000만원",
                    },
                }

                record = service.format_record_for_upsert(cert)

                assert "무역" in record["chunk_text"]
                assert "물류" in record["chunk_text"]
                assert "관세사" in record["chunk_text"]

    def test_upsert_certificates_batch_integrated(self):
        """배치 업서트 테스트 (OpenAI 임베딩)."""
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

                    certs = [
                        {
                            "id": "cert-001",
                            "title": "정보처리기사",
                            "categories": [{"code": "T", "name": "국가기술자격"}],
                            "overview": "IT 자격증",
                        },
                        {
                            "id": "cert-002",
                            "title": "관세사",
                            "categories": [{"code": "S", "name": "국가전문자격"}],
                            "overview": "무역 자격증",
                        },
                    ]

                    service.upsert_certificates_batch_integrated(certs)

                    # create_embeddings_batch가 호출되었는지 확인
                    mock_embed_instance.create_embeddings_batch.assert_called_once()
                    # collection.upsert가 호출되었는지 확인
                    mock_collection.upsert.assert_called_once()


class TestEmbeddingServiceSimplified:
    """단순화된 EmbeddingService (텍스트 포맷팅만) 테스트."""

    def test_format_certificate_text_only(self):
        """텍스트 포맷팅만 테스트."""
        from app.services.embedding_service import EmbeddingService

        # api_key 없이 초기화 가능해야 함
        service = EmbeddingService(api_key=None)

        cert = {
            "title": "정보처리기사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "overview": "IT 자격증",
        }

        result = service.format_certificate_for_embedding(cert)

        assert "정보처리기사" in result
        assert "국가기술자격" in result
