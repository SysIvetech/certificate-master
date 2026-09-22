"""벡터 스토어 테스트 격리 테스트.

요구사항:
1. 테스트 환경에서 별도의 컬렉션 사용
2. 프로덕션 데이터와 테스트 데이터 분리
"""

from unittest.mock import MagicMock, patch


class TestVectorStoreCollectionIsolation:
    """벡터 스토어 컬렉션 격리 테스트."""

    def test_vector_store_accepts_custom_collection_name(self):
        """VectorStoreService가 커스텀 컬렉션 이름을 받을 수 있어야 합니다."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "production-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.embedding.vector_store import VectorStoreService

                # 커스텀 컬렉션 이름 전달
                VectorStoreService(collection_name="test-collection")

                # 커스텀 컬렉션 이름으로 생성되어야 함
                mock_client.get_or_create_collection.assert_called_once()
                call_args = mock_client.get_or_create_collection.call_args
                assert (
                    call_args.kwargs.get("name") == "test-collection"
                    or call_args[1].get("name") == "test-collection"
                )

    def test_vector_store_uses_default_collection_when_not_specified(self):
        """컬렉션 이름을 지정하지 않으면 설정값을 사용해야 합니다."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "default-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.embedding.vector_store import VectorStoreService

                # 컬렉션 이름 미지정
                VectorStoreService()

                # 설정값 컬렉션 이름으로 생성되어야 함
                mock_client.get_or_create_collection.assert_called_once()
                call_args = mock_client.get_or_create_collection.call_args
                assert (
                    call_args.kwargs.get("name") == "default-collection"
                    or call_args[1].get("name") == "default-collection"
                )


class TestVectorStoreClearAll:
    """벡터 스토어 전체 삭제 테스트."""

    def test_clear_all_method_exists(self):
        """VectorStoreService에 clear_all 메서드가 있어야 합니다."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.embedding.vector_store import VectorStoreService

                service = VectorStoreService()

                # clear_all 메서드 존재 확인
                assert hasattr(service, "clear_all"), "clear_all 메서드가 없습니다"
                assert callable(getattr(service, "clear_all"))

    def test_clear_all_deletes_collection(self):
        """clear_all이 컬렉션을 삭제하고 재생성해야 합니다."""
        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection

                from app.services.embedding.vector_store import VectorStoreService

                service = VectorStoreService()
                service.clear_all()

                # 컬렉션 삭제 호출 확인
                mock_client.delete_collection.assert_called_once_with(
                    name="test-collection"
                )
