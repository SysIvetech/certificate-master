"""VectorStoreService의 DB vector_id 동기화 테스트.

TDD: RED phase - 테스트 먼저 작성.

기능:
1. ChromaDB 업로드 후 DB에 vector_id 저장
2. ChromaDB 삭제 후 DB에서 vector_id 초기화
3. vector_id가 없는 자격증 조회

MariaDB(SQLAlchemy)로 마이그레이션됨 (2026-01-22).
"""

from unittest.mock import MagicMock, patch


class TestVectorStoreDbSync:
    """VectorStoreService의 DB 동기화 기능 테스트."""

    def test_sync_vector_id_to_db_success(self):
        """ChromaDB 업로드 후 DB에 vector_id 저장 테스트."""
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
                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    # Mock SQLAlchemy session
                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # Mock certificate query
                    mock_cert = MagicMock()
                    mock_cert.vector_id = None
                    mock_session.query.return_value.filter.return_value.first.return_value = (
                        mock_cert
                    )

                    # Execute
                    result = service.sync_vector_id_to_db(
                        cert_id="cert-123", vector_id="vec-123"
                    )

                    # Verify
                    assert mock_cert.vector_id == "vec-123"
                    mock_session.commit.assert_called_once()
                    mock_session.close.assert_called_once()
                    assert result is True

    def test_sync_vector_id_to_db_batch(self):
        """배치로 여러 자격증의 vector_id 저장 테스트."""
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
                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    # Mock SQLAlchemy session
                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # Mock certificate queries - return mock objects for each call
                    # 4개 필요: 3개 업데이트 + 1개 검증 쿼리
                    mock_certs = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
                    mock_certs[3].vector_id = "vec-1"  # 검증용 cert
                    mock_session.query.return_value.filter.return_value.first.side_effect = (
                        mock_certs
                    )

                    # Execute batch sync
                    mappings = [
                        ("cert-1", "vec-1"),
                        ("cert-2", "vec-2"),
                        ("cert-3", "vec-3"),
                    ]
                    result = service.sync_vector_ids_to_db_batch(mappings)

                    # Verify (B5: 상세 결과 딕셔너리 반환)
                    assert result["success"] == 3
                    mock_session.commit.assert_called_once()
                    mock_session.close.assert_called_once()

    def test_clear_vector_id_in_db(self):
        """DB에서 vector_id 초기화 테스트."""
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
                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    # Mock SQLAlchemy session
                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # Mock certificate query
                    mock_cert = MagicMock()
                    mock_cert.vector_id = "vec-123"
                    mock_session.query.return_value.filter.return_value.first.return_value = (
                        mock_cert
                    )

                    # Execute
                    result = service.clear_vector_id_in_db("cert-123")

                    # Verify
                    assert mock_cert.vector_id is None
                    mock_session.commit.assert_called_once()
                    mock_session.close.assert_called_once()
                    assert result is True

    def test_get_certificates_without_vector_id(self):
        """vector_id가 없는 자격증 조회 테스트."""
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
                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    # Mock SQLAlchemy session
                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # Mock certificate query results
                    mock_cert1 = MagicMock()
                    mock_cert1.to_dict.return_value = {
                        "id": "cert-1",
                        "title": "자격증1",
                        "vector_id": None,
                    }
                    mock_cert2 = MagicMock()
                    mock_cert2.to_dict.return_value = {
                        "id": "cert-2",
                        "title": "자격증2",
                        "vector_id": None,
                    }

                    mock_session.query.return_value.filter.return_value.filter.return_value.all.return_value = [
                        mock_cert1,
                        mock_cert2,
                    ]

                    # Execute
                    result = service.get_certificates_without_vector_id()

                    # Verify
                    assert len(result) == 2
                    assert result[0]["title"] == "자격증1"
                    mock_session.close.assert_called_once()

    def test_get_certificates_with_vector_id(self):
        """vector_id가 있는 자격증 조회 테스트."""
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
                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    # Mock SQLAlchemy session
                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # Mock certificate query results
                    mock_cert1 = MagicMock()
                    mock_cert1.to_dict.return_value = {
                        "id": "cert-1",
                        "title": "자격증1",
                        "vector_id": "vec-1",
                    }
                    mock_cert2 = MagicMock()
                    mock_cert2.to_dict.return_value = {
                        "id": "cert-2",
                        "title": "자격증2",
                        "vector_id": "vec-2",
                    }

                    mock_session.query.return_value.filter.return_value.all.return_value = [
                        mock_cert1,
                        mock_cert2,
                    ]

                    # Execute
                    result = service.get_certificates_with_vector_id()

                    # Verify
                    assert len(result) == 2
                    assert result[0]["vector_id"] == "vec-1"
                    mock_session.close.assert_called_once()

    def test_upsert_with_db_sync(self):
        """ChromaDB 업로드 + DB 동기화 통합 테스트."""
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
                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    # Mock SQLAlchemy session
                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # Mock certificate query
                    mock_cert = MagicMock()
                    mock_session.query.return_value.filter.return_value.first.return_value = (
                        mock_cert
                    )

                    # Execute - 새로운 메서드 사용
                    cert_id = "cert-123"
                    embedding = [0.1] * 1024
                    metadata = {"title": "정보처리기사"}

                    service.upsert_certificate_with_sync(cert_id, embedding, metadata)

                    # Verify ChromaDB upsert
                    mock_collection.upsert.assert_called_once()

                    # Verify DB sync
                    assert mock_cert.vector_id == cert_id
                    mock_session.commit.assert_called_once()

    def test_delete_with_db_sync(self):
        """ChromaDB 삭제 + DB 동기화 통합 테스트."""
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
                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    # Mock SQLAlchemy session
                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # Mock certificate query
                    mock_cert = MagicMock()
                    mock_cert.vector_id = "cert-123"
                    mock_session.query.return_value.filter.return_value.first.return_value = (
                        mock_cert
                    )

                    # Execute
                    service.delete_certificate_with_sync("cert-123")

                    # Verify ChromaDB delete
                    mock_collection.delete.assert_called_once_with(ids=["cert-123"])

                    # Verify DB sync (vector_id = None)
                    assert mock_cert.vector_id is None
                    mock_session.commit.assert_called_once()


class TestSyncResultTracking:
    """B5: sync_vector_ids_to_db_batch 결과 추적 개선 테스트."""

    def test_sync_batch_returns_detailed_result(self):
        """sync_vector_ids_to_db_batch가 상세 결과를 반환하는지 테스트.

        B5: 성공 개수만 반환하는 대신 상세 결과 딕셔너리 반환.
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
                mock_client.heartbeat.return_value = 1234567890

                with patch(
                    "app.services.embedding.vector_store._get_db_session"
                ) as mock_get_session:
                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # cert-1, cert-2는 성공, cert-3는 not found
                    mock_cert1 = MagicMock()
                    mock_cert2 = MagicMock()
                    mock_cert_verify = MagicMock()
                    mock_cert_verify.vector_id = "vec-1"

                    mock_session.query.return_value.filter.return_value.first.side_effect = [
                        mock_cert1,  # cert-1 found
                        mock_cert2,  # cert-2 found
                        None,  # cert-3 not found
                        mock_cert_verify,  # 검증용
                    ]

                    mappings = [
                        ("cert-1", "vec-1"),
                        ("cert-2", "vec-2"),
                        ("cert-3", "vec-3"),
                    ]
                    result = service.sync_vector_ids_to_db_batch(mappings)

                    # B5: 상세 결과 반환
                    assert isinstance(result, dict)
                    assert result["success"] == 2
                    assert "cert-3" in result["not_found_ids"]

    def test_sync_batch_returns_errors_on_failure(self):
        """DB 에러 발생 시 에러 정보를 반환하는지 테스트."""
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

                with patch(
                    "app.services.embedding.vector_store._get_db_session"
                ) as mock_get_session:
                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # commit에서 에러 발생
                    mock_session.commit.side_effect = Exception("DB connection lost")
                    mock_session.query.return_value.filter.return_value.first.return_value = (
                        MagicMock()
                    )

                    mappings = [("cert-1", "vec-1")]
                    result = service.sync_vector_ids_to_db_batch(mappings)

                    # B5: 에러 정보 포함
                    assert isinstance(result, dict)
                    assert result["success"] == 0
                    assert len(result["errors"]) > 0


class TestCertificateSchemaVectorId:
    """Certificate 스키마의 vector_id 필드 테스트."""

    def test_certificate_schema_has_vector_id(self):
        """Certificate 스키마에 vector_id 필드가 있는지 테스트."""
        from app.schemas.certificate import Certificate

        # Certificate 스키마의 필드 확인
        fields = Certificate.model_fields
        assert "vector_id" in fields, "Certificate 스키마에 vector_id 필드가 필요합니다"

    def test_certificate_schema_vector_id_optional(self):
        """vector_id가 Optional인지 테스트."""
        from app.schemas.certificate import Certificate

        fields = Certificate.model_fields
        # Optional 필드이므로 None 허용
        vector_id_field = fields.get("vector_id")
        assert vector_id_field is not None
        # default가 None이거나 Optional 타입이어야 함

    def test_certificate_update_schema_has_vector_id(self):
        """CertificateUpdate 스키마에 vector_id 필드가 있는지 테스트."""
        from app.schemas.certificate import CertificateUpdate

        fields = CertificateUpdate.model_fields
        assert (
            "vector_id" in fields
        ), "CertificateUpdate 스키마에 vector_id 필드가 필요합니다"


class TestResetCertificateData:
    """벡터 삭제 시 DB 자격증 데이터 리셋 테스트.

    요구사항:
    - 유지: id, series, title, raw_id, categories
    - 리셋: 나머지 모든 필드 (overview, difficulty, study_period_days 등)
    """

    def test_reset_certificate_data_in_db(self):
        """단일 자격증 데이터 리셋 테스트."""
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
                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    # Mock SQLAlchemy session
                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # Mock certificate with enriched data
                    mock_cert = MagicMock()
                    mock_cert.overview = "기존 개요"
                    mock_cert.difficulty = 3
                    mock_cert.study_period_days = 90
                    mock_cert.vector_id = "vec-123"
                    mock_cert.passing_rate = 45.5
                    mock_cert.view_count = 100
                    mock_session.query.return_value.filter.return_value.first.return_value = (
                        mock_cert
                    )

                    # Execute
                    result = service.reset_certificate_data_in_db("cert-123")

                    # Verify - 보강 데이터가 리셋되었는지 확인
                    assert mock_cert.overview is None
                    assert mock_cert.difficulty is None
                    assert mock_cert.study_period_days is None
                    assert mock_cert.vector_id is None
                    assert mock_cert.passing_rate is None
                    assert mock_cert.view_count == 0
                    mock_session.commit.assert_called_once()
                    mock_session.close.assert_called_once()
                    assert result is True

    def test_reset_certificates_data_in_db_batch(self):
        """배치 자격증 데이터 리셋 테스트."""
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
                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    # Mock SQLAlchemy session
                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # Mock certificate queries
                    mock_cert1 = MagicMock()
                    mock_cert1.overview = "개요1"
                    mock_cert1.vector_id = "vec-1"
                    mock_cert2 = MagicMock()
                    mock_cert2.overview = "개요2"
                    mock_cert2.vector_id = "vec-2"

                    mock_session.query.return_value.filter.return_value.first.side_effect = [
                        mock_cert1,
                        mock_cert2,
                        None,  # cert-3 not found
                    ]

                    # Execute
                    cert_ids = ["cert-1", "cert-2", "cert-3"]
                    result = service.reset_certificates_data_in_db_batch(cert_ids)

                    # Verify
                    assert mock_cert1.overview is None
                    assert mock_cert1.vector_id is None
                    assert mock_cert2.overview is None
                    assert mock_cert2.vector_id is None
                    assert result["success"] == 2
                    assert "cert-3" in result["not_found_ids"]
                    mock_session.commit.assert_called_once()

    def test_delete_certificate_with_reset(self):
        """ChromaDB 삭제 + DB 데이터 리셋 통합 테스트."""
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
                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    # Mock SQLAlchemy session
                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # Mock certificate
                    mock_cert = MagicMock()
                    mock_cert.overview = "기존 개요"
                    mock_cert.vector_id = "cert-123"
                    mock_session.query.return_value.filter.return_value.first.return_value = (
                        mock_cert
                    )

                    # Execute
                    service.delete_certificate_with_reset("cert-123")

                    # Verify ChromaDB delete
                    mock_collection.delete.assert_called_once_with(ids=["cert-123"])

                    # Verify DB reset (not just vector_id, but all enriched data)
                    assert mock_cert.overview is None
                    assert mock_cert.vector_id is None
                    mock_session.commit.assert_called_once()

    def test_delete_certificates_batch_with_reset(self):
        """배치 ChromaDB 삭제 + DB 데이터 리셋 통합 테스트."""
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
                    from app.services.vector_store import VectorStoreService

                    service = VectorStoreService()

                    # Mock SQLAlchemy session
                    mock_session = MagicMock()
                    mock_get_session.return_value = mock_session

                    # Mock certificates
                    mock_cert1 = MagicMock()
                    mock_cert1.overview = "개요1"
                    mock_cert2 = MagicMock()
                    mock_cert2.overview = "개요2"

                    mock_session.query.return_value.filter.return_value.first.side_effect = [
                        mock_cert1,
                        mock_cert2,
                    ]

                    # Execute
                    cert_ids = ["cert-1", "cert-2"]
                    result = service.delete_certificates_batch_with_reset(cert_ids)

                    # Verify ChromaDB batch delete
                    mock_collection.delete.assert_called_once_with(ids=cert_ids)

                    # Verify DB reset
                    assert mock_cert1.overview is None
                    assert mock_cert2.overview is None
                    assert result["success"] == 2
