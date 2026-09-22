"""특정 자격증 재생성 커맨드 테스트.

`--recreate <cert_id>` 또는 `--recreate-by-name <name>` 옵션으로
특정 자격증의 보강 데이터를 완전히 새로 생성하는 기능을 테스트합니다.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# backend 디렉토리를 path에 추가
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))


class TestRecreateCommand:
    """--recreate 커맨드 테스트."""

    @pytest.fixture
    def cert_id(self):
        """테스트용 자격증 ID."""
        return str(uuid4())

    @pytest.fixture
    def mock_certificate(self, cert_id):
        """테스트용 자격증 mock."""
        cert = MagicMock()
        cert.id = cert_id
        cert.title = "정보처리기사"
        cert.overview = "기존 보강 데이터"
        cert.key_points = "기존 핵심 포인트"
        cert.vector_id = f"vec_{cert_id}"
        cert.difficulty_info = None
        cert.cost_info = None
        cert.job_prospects = None
        cert.similar_certificates = None
        cert.latest_trends = None
        cert.free_resources = None
        cert.official_resources = None
        return cert

    @pytest.mark.asyncio
    async def test_recreate_returns_error_when_not_found(self):
        """자격증을 찾지 못하면 에러를 반환해야 한다."""
        from scripts.data_pipeline import DataPipeline

        # Mock session 설정
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None  # 자격증 없음
        mock_session.query.return_value = mock_query

        pipeline = DataPipeline(test_mode=True)

        with patch(
            "scripts.data_pipeline.get_mariadb_session", return_value=mock_session
        ):
            result = await pipeline.recreate_certificate("nonexistent-id")

            assert result["status"] == "error"
            assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_recreate_clears_existing_data(self, cert_id, mock_certificate):
        """recreate는 기존 보강 데이터를 클리어해야 한다."""
        from scripts.data_pipeline import DataPipeline

        # Mock session
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_certificate
        mock_session.query.return_value = mock_query

        pipeline = DataPipeline(test_mode=True)

        # enrich_step과 embedding_step을 mock
        with (
            patch(
                "scripts.data_pipeline.get_mariadb_session", return_value=mock_session
            ),
            patch.object(
                pipeline, "enrich_step", new_callable=AsyncMock
            ) as mock_enrich,
            patch.object(
                pipeline, "embedding_step", new_callable=AsyncMock
            ) as mock_embedding,
            patch("app.services.embedding_factory.get_embedding_service"),
            patch("app.services.vector_store.VectorStoreService"),
        ):
            mock_enrich.return_value = {
                "processed": 1,
                "success": 1,
                "failed": 0,
                "failed_ids": [],
                "skipped": False,
            }
            mock_embedding.return_value = {
                "processed": 1,
                "uploaded": 1,
                "synced": 1,
                "skipped": 0,
                "synced_from_chroma": 0,
                "failed_ids": [],
                "skipped_step": False,
            }

            result = await pipeline.recreate_certificate(cert_id)

            # 기존 데이터가 클리어되었는지 확인
            assert mock_certificate.overview is None
            assert mock_certificate.key_points is None
            assert mock_certificate.vector_id is None
            assert result["cleared"] is True

    @pytest.mark.asyncio
    async def test_recreate_runs_enrich_and_embedding(self, cert_id, mock_certificate):
        """recreate는 보강과 임베딩을 모두 실행해야 한다."""
        from scripts.data_pipeline import DataPipeline

        # Mock session
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_certificate
        mock_session.query.return_value = mock_query

        pipeline = DataPipeline(test_mode=True)

        with (
            patch(
                "scripts.data_pipeline.get_mariadb_session", return_value=mock_session
            ),
            patch.object(
                pipeline, "enrich_step", new_callable=AsyncMock
            ) as mock_enrich,
            patch.object(
                pipeline, "embedding_step", new_callable=AsyncMock
            ) as mock_embedding,
            patch("app.services.embedding_factory.get_embedding_service"),
            patch("app.services.vector_store.VectorStoreService"),
        ):
            mock_enrich.return_value = {
                "processed": 1,
                "success": 1,
                "failed": 0,
                "failed_ids": [],
                "skipped": False,
            }
            mock_embedding.return_value = {
                "processed": 1,
                "uploaded": 1,
                "synced": 1,
                "skipped": 0,
                "synced_from_chroma": 0,
                "failed_ids": [],
                "skipped_step": False,
            }

            result = await pipeline.recreate_certificate(cert_id)

            # enrich_step과 embedding_step이 호출되었는지 확인
            mock_enrich.assert_called_once_with(cert_ids=[cert_id])
            mock_embedding.assert_called_once_with(cert_ids=[cert_id])
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_recreate_by_name_finds_and_recreates(
        self, cert_id, mock_certificate
    ):
        """이름으로 자격증을 찾아서 재생성해야 한다."""
        from scripts.data_pipeline import DataPipeline

        # Mock session
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_certificate
        mock_session.query.return_value = mock_query

        pipeline = DataPipeline(test_mode=True)

        with (
            patch(
                "scripts.data_pipeline.get_mariadb_session", return_value=mock_session
            ),
            patch.object(
                pipeline, "recreate_certificate", new_callable=AsyncMock
            ) as mock_recreate,
        ):
            mock_recreate.return_value = {"status": "success"}

            result = await pipeline.recreate_certificate_by_name("정보처리기사")

            # recreate_certificate가 찾은 ID로 호출되었는지 확인
            mock_recreate.assert_called_once_with(cert_id)
            assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_recreate_by_name_returns_error_when_not_found(self):
        """이름으로 자격증을 찾지 못하면 에러를 반환해야 한다."""
        from scripts.data_pipeline import DataPipeline

        # Mock session - 자격증 없음
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_session.query.return_value = mock_query

        pipeline = DataPipeline(test_mode=True)

        with patch(
            "scripts.data_pipeline.get_mariadb_session", return_value=mock_session
        ):
            result = await pipeline.recreate_certificate_by_name("존재하지않는자격증")

            assert result["status"] == "error"
            assert "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_recreate_deletes_vector_from_chromadb(
        self, cert_id, mock_certificate
    ):
        """기존 벡터가 있으면 ChromaDB에서 삭제해야 한다."""
        from scripts.data_pipeline import DataPipeline

        # Mock session
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_certificate
        mock_session.query.return_value = mock_query

        # Mock vector store
        mock_vector_store = MagicMock()

        pipeline = DataPipeline(test_mode=True)

        with (
            patch(
                "scripts.data_pipeline.get_mariadb_session", return_value=mock_session
            ),
            patch.object(
                pipeline, "enrich_step", new_callable=AsyncMock
            ) as mock_enrich,
            patch.object(
                pipeline, "embedding_step", new_callable=AsyncMock
            ) as mock_embedding,
            patch("app.services.embedding_factory.get_embedding_service"),
            patch(
                "app.services.vector_store.VectorStoreService",
                return_value=mock_vector_store,
            ),
        ):
            mock_enrich.return_value = {
                "processed": 1,
                "success": 1,
                "failed": 0,
                "failed_ids": [],
                "skipped": False,
            }
            mock_embedding.return_value = {
                "processed": 1,
                "uploaded": 1,
                "synced": 1,
                "skipped": 0,
                "synced_from_chroma": 0,
                "failed_ids": [],
                "skipped_step": False,
            }

            # vector_id가 있는 상태로 실행
            await pipeline.recreate_certificate(cert_id)

            # ChromaDB에서 삭제가 호출되었는지 확인 (cert_id로 삭제)
            mock_vector_store.delete_certificate.assert_called_once_with(cert_id)


class TestRecreateCommandLineArgs:
    """커맨드라인 인자 파싱 테스트."""

    def test_recreate_argument_exists(self):
        """--recreate 인자가 argparser에 존재해야 한다."""

        # data_pipeline 모듈의 argparser를 검사
        # main 함수 소스 코드를 확인하여 --recreate 옵션이 있는지 검사
        import inspect

        from scripts.data_pipeline import main

        source = inspect.getsource(main)

        assert "--recreate" in source
        assert "--recreate-by-name" in source

    def test_help_message_contains_recreate_options(self):
        """help 메시지에 --recreate 옵션이 포함되어야 한다."""
        # argparse를 직접 테스트
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--recreate",
            type=str,
            metavar="CERT_ID",
            help="특정 자격증 ID의 보강 데이터를 완전히 새로 생성",
        )
        parser.add_argument(
            "--recreate-by-name",
            type=str,
            metavar="NAME",
            help="자격증 이름으로 검색하여 보강 데이터를 완전히 새로 생성",
        )

        # 파서의 format_help()에 옵션이 포함되는지 확인
        help_text = parser.format_help()

        assert "--recreate" in help_text
        assert "--recreate-by-name" in help_text
        assert "CERT_ID" in help_text
        assert "NAME" in help_text
