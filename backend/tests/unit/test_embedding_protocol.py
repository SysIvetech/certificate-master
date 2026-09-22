"""EmbeddingServiceProtocol 및 팩토리 테스트."""

from unittest.mock import MagicMock, patch


class TestEmbeddingServiceProtocol:
    """EmbeddingServiceProtocol 테스트."""

    def test_embedding_service_implements_protocol(self):
        """EmbeddingService가 프로토콜을 구현하는지 테스트."""
        from app.services.embedding_protocol import EmbeddingServiceProtocol
        from app.services.embedding_service import EmbeddingService

        # EmbeddingService 인스턴스가 프로토콜을 만족하는지 확인
        service = EmbeddingService()
        assert isinstance(service, EmbeddingServiceProtocol)

    def test_protocol_has_dimensions_property(self):
        """프로토콜이 dimensions 속성을 요구하는지 테스트."""
        from app.services.embedding_protocol import EmbeddingServiceProtocol

        # 프로토콜이 dimensions를 요구함
        assert hasattr(EmbeddingServiceProtocol, "dimensions")

    def test_protocol_has_create_embedding_method(self):
        """프로토콜이 create_embedding 메서드를 요구하는지 테스트."""
        from app.services.embedding_protocol import EmbeddingServiceProtocol

        assert hasattr(EmbeddingServiceProtocol, "create_embedding")

    def test_protocol_has_create_embeddings_batch_method(self):
        """프로토콜이 create_embeddings_batch 메서드를 요구하는지 테스트."""
        from app.services.embedding_protocol import EmbeddingServiceProtocol

        assert hasattr(EmbeddingServiceProtocol, "create_embeddings_batch")


class TestEmbeddingFactory:
    """임베딩 팩토리 테스트."""

    def test_get_embedding_service_returns_openai(self):
        """팩토리가 OpenAI 서비스를 반환하는지 테스트."""
        from app.services.embedding.factory import get_embedding_service
        from app.services.embedding.service import EmbeddingService

        service = get_embedding_service()
        assert isinstance(service, EmbeddingService)


class TestVectorStoreServiceDI:
    """VectorStoreService 의존성 주입 테스트."""

    def test_init_with_default_embedding_service(self):
        """기본 EmbeddingService가 생성되는지 테스트."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.embedding_service import EmbeddingService
                from app.services.vector_store import VectorStoreService

                # embedding_service 미지정 시 기본 EmbeddingService 생성
                service = VectorStoreService()
                assert isinstance(service.embedding_service, EmbeddingService)

    def test_init_with_injected_embedding_service(self):
        """외부에서 주입된 임베딩 서비스가 사용되는지 테스트."""
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

                # Mock 임베딩 서비스 주입
                mock_embedding_service = MagicMock()
                mock_embedding_service.dimensions = 1024
                mock_embedding_service.create_embedding.return_value = [0.1] * 1024
                mock_embedding_service.create_embeddings_batch.return_value = [
                    [0.1] * 1024
                ]

                service = VectorStoreService(embedding_service=mock_embedding_service)

                # 주입된 서비스가 사용되어야 함
                assert service.embedding_service is mock_embedding_service

    def test_injected_service_used_for_search(self):
        """검색 시 주입된 임베딩 서비스가 사용되는지 테스트."""
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

                # Mock 임베딩 서비스 주입
                mock_embedding_service = MagicMock()
                mock_embedding_service.create_embedding.return_value = [0.1] * 1024

                service = VectorStoreService(embedding_service=mock_embedding_service)
                service.search_records("certificates", "테스트 쿼리", top_k=5)

                # 주입된 서비스의 create_embedding이 호출되어야 함
                mock_embedding_service.create_embedding.assert_called_once_with(
                    "테스트 쿼리"
                )
