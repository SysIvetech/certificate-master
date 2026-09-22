"""데이터 파이프라인 통합 테스트.

테스트 대상:
1. 파이프라인이 enrich → embedding 순서로 실행되는지
2. 옵션 처리가 올바른지
3. 단계별 건너뛰기가 동작하는지
"""

from unittest.mock import AsyncMock

import pytest


class TestDataPipelineSteps:
    """파이프라인 단계 테스트."""

    @pytest.mark.asyncio
    async def test_pipeline_runs_enrich_then_embedding(self):
        """파이프라인이 enrich → embedding 순서로 실행되어야 한다."""
        from scripts.data_pipeline import DataPipeline

        pipeline = DataPipeline()

        # Mock 설정
        pipeline.enrich_step = AsyncMock(return_value={"processed": 5, "success": 5})
        pipeline.embedding_step = AsyncMock(
            return_value={"processed": 5, "uploaded": 5}
        )

        result = await pipeline.run(limit=5)

        # 순서 검증: enrich가 먼저 호출되고, 그 다음 embedding
        pipeline.enrich_step.assert_called_once()
        pipeline.embedding_step.assert_called_once()

        # 결과 검증
        assert result["enrich"]["processed"] == 5
        assert result["embedding"]["uploaded"] == 5

    @pytest.mark.asyncio
    async def test_pipeline_skip_enrich(self):
        """--skip-enrich 옵션으로 enrich 단계를 건너뛸 수 있어야 한다."""
        from scripts.data_pipeline import DataPipeline

        pipeline = DataPipeline()
        pipeline.enrich_step = AsyncMock()
        pipeline.embedding_step = AsyncMock(
            return_value={"processed": 5, "uploaded": 5}
        )

        result = await pipeline.run(limit=5, skip_enrich=True)

        # enrich는 호출되지 않아야 함
        pipeline.enrich_step.assert_not_called()
        # embedding은 호출되어야 함
        pipeline.embedding_step.assert_called_once()

        assert result["enrich"]["skipped"] is True
        assert result["embedding"]["uploaded"] == 5

    @pytest.mark.asyncio
    async def test_pipeline_skip_embedding(self):
        """--skip-embedding 옵션으로 embedding 단계를 건너뛸 수 있어야 한다."""
        from scripts.data_pipeline import DataPipeline

        pipeline = DataPipeline()
        pipeline.enrich_step = AsyncMock(return_value={"processed": 5, "success": 5})
        pipeline.embedding_step = AsyncMock()

        result = await pipeline.run(limit=5, skip_embedding=True)

        # enrich는 호출되어야 함
        pipeline.enrich_step.assert_called_once()
        # embedding은 호출되지 않아야 함
        pipeline.embedding_step.assert_not_called()

        assert result["enrich"]["success"] == 5
        assert result["embedding"]["skipped_step"] is True  # 코드와 일치하도록 수정


class TestDataPipelineOptions:
    """파이프라인 옵션 테스트."""

    @pytest.mark.asyncio
    async def test_pipeline_test_mode(self):
        """test 모드는 limit=1로 동작해야 한다."""
        from scripts.data_pipeline import DataPipeline

        pipeline = DataPipeline()
        pipeline.enrich_step = AsyncMock(return_value={"processed": 1, "success": 1})
        pipeline.embedding_step = AsyncMock(
            return_value={"processed": 1, "uploaded": 1}
        )

        await pipeline.run(test_mode=True)

        # test 모드는 limit=1
        enrich_call_args = pipeline.enrich_step.call_args
        assert enrich_call_args.kwargs.get("limit") == 1

    @pytest.mark.asyncio
    async def test_pipeline_limit_option(self):
        """limit 옵션이 각 단계에 전달되어야 한다."""
        from scripts.data_pipeline import DataPipeline

        pipeline = DataPipeline()
        pipeline.enrich_step = AsyncMock(return_value={"processed": 10, "success": 10})
        pipeline.embedding_step = AsyncMock(
            return_value={"processed": 10, "uploaded": 10}
        )

        await pipeline.run(limit=10)

        # limit이 각 단계에 전달됨
        enrich_call_args = pipeline.enrich_step.call_args
        embedding_call_args = pipeline.embedding_step.call_args

        assert enrich_call_args.kwargs.get("limit") == 10
        assert embedding_call_args.kwargs.get("limit") == 10

    @pytest.mark.asyncio
    async def test_pipeline_skip_existing_option(self):
        """skip_existing 옵션이 embedding 단계에 전달되어야 한다."""
        from scripts.data_pipeline import DataPipeline

        pipeline = DataPipeline()
        pipeline.enrich_step = AsyncMock(return_value={"processed": 5, "success": 5})
        pipeline.embedding_step = AsyncMock(
            return_value={"processed": 5, "uploaded": 5}
        )

        await pipeline.run(limit=5, skip_existing=True)

        embedding_call_args = pipeline.embedding_step.call_args
        assert embedding_call_args.kwargs.get("skip_existing") is True


class TestDataPipelineErrorHandling:
    """파이프라인 에러 처리 테스트."""

    @pytest.mark.asyncio
    async def test_pipeline_continues_on_enrich_error(self):
        """enrich 단계에서 부분 실패해도 embedding 단계가 실행되어야 한다."""
        from scripts.data_pipeline import DataPipeline

        pipeline = DataPipeline()
        # enrich가 부분 성공 (5개 중 3개 성공)
        pipeline.enrich_step = AsyncMock(
            return_value={"processed": 5, "success": 3, "failed": 2}
        )
        pipeline.embedding_step = AsyncMock(
            return_value={"processed": 3, "uploaded": 3}
        )

        result = await pipeline.run(limit=5)

        # embedding 단계도 실행되어야 함
        pipeline.embedding_step.assert_called_once()
        assert result["enrich"]["failed"] == 2
        assert result["embedding"]["uploaded"] == 3

    @pytest.mark.asyncio
    async def test_pipeline_stops_on_critical_error(self):
        """enrich 단계에서 치명적 에러 발생 시 중단되어야 한다."""
        from scripts.data_pipeline import DataPipeline

        pipeline = DataPipeline()
        pipeline.enrich_step = AsyncMock(side_effect=Exception("DB Connection Failed"))
        pipeline.embedding_step = AsyncMock()

        with pytest.raises(Exception, match="DB Connection Failed"):
            await pipeline.run(limit=5)

        # embedding 단계는 실행되지 않아야 함
        pipeline.embedding_step.assert_not_called()
