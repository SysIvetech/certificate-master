"""하이브리드 검색 서비스 (Dense + Sparse + RRF) 테스트."""

from unittest.mock import MagicMock

import pytest

from app.services.search.hybrid_search_service import HybridSearchService


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.NAMESPACE = "certificates"
    store.search_records = MagicMock(
        return_value=[
            {"id": "cert-A", "score": 0.8, "metadata": {}},
            {"id": "cert-B", "score": 0.6, "metadata": {}},
            {"id": "cert-C", "score": 0.4, "metadata": {}},
        ]
    )
    return store


@pytest.fixture
def mock_bm25():
    bm25 = MagicMock()
    bm25.is_ready.return_value = True
    bm25.search.return_value = [
        {"id": "cert-B", "score": 5.0, "domain": "IT"},
        {"id": "cert-D", "score": 3.0, "domain": "IT"},
        {"id": "cert-A", "score": 1.0, "domain": "IT"},
    ]
    return bm25


@pytest.fixture
def service(mock_vector_store, mock_bm25):
    return HybridSearchService(vector_store=mock_vector_store, bm25_service=mock_bm25)


class TestRRFFusion:
    @pytest.mark.asyncio
    async def test_merges_dense_and_sparse(self, service):
        results = await service.search("정보처리기사", top_k=5)
        ids = [r["id"] for r in results]
        assert ids[0] == "cert-B"  # highest combined RRF

    @pytest.mark.asyncio
    async def test_includes_results_from_both(self, service):
        results = await service.search("테스트", top_k=10)
        ids = [r["id"] for r in results]
        assert "cert-C" in ids  # Dense only
        assert "cert-D" in ids  # Sparse only

    @pytest.mark.asyncio
    async def test_top_k_limits_results(self, service):
        results = await service.search("테스트", top_k=2)
        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_results_have_rrf_score(self, service):
        results = await service.search("테스트", top_k=5)
        assert all("rrf_score" in r for r in results)
        assert all(r["rrf_score"] > 0 for r in results)

    @pytest.mark.asyncio
    async def test_results_sorted_by_rrf_score(self, service):
        results = await service.search("테스트", top_k=5)
        scores = [r["rrf_score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_rrf_formula_correct(self, service):
        results = await service.search("테스트", top_k=10)
        cert_b = next(r for r in results if r["id"] == "cert-B")
        expected = 1 / 62 + 1 / 61  # Dense rank=2, Sparse rank=1
        assert abs(cert_b["rrf_score"] - expected) < 0.0001

    @pytest.mark.asyncio
    async def test_search_stats_returned(self, service):
        await service.search("테스트", top_k=5)
        stats = service.last_search_stats
        assert stats["dense_count"] == 3
        assert stats["sparse_count"] == 3
        assert stats["merged_count"] > 0
        assert stats["elapsed_ms"] >= 0

    @pytest.mark.asyncio
    async def test_empty_query(self, service):
        service._vector_store.search_records.return_value = []
        service._bm25_service.search.return_value = []
        results = await service.search("", top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_records_called_with_namespace(self, service):
        """search_records에 namespace 인자가 전달되는지 확인."""
        await service.search("테스트", top_k=5)
        service._vector_store.search_records.assert_called_once_with(
            "certificates", "테스트", 15, filter_dict=None
        )

    @pytest.mark.asyncio
    async def test_bm25_called_with_correct_args(self, service):
        """BM25 search에 올바른 인자가 전달되는지 확인."""
        await service.search("테스트", top_k=5, domains=["IT"])
        service._bm25_service.search.assert_called_once_with("테스트", 15, ["IT"])

    @pytest.mark.asyncio
    async def test_dense_search_passes_domain_filter(self, service):
        """domains가 주어지면 Dense 검색에 filter_dict가 전달되는지 확인."""
        await service.search("테스트", top_k=5, domains=["IT/소프트웨어"])
        service._vector_store.search_records.assert_called_once_with(
            "certificates",
            "테스트",
            15,
            filter_dict={"domain": {"$in": ["IT/소프트웨어"]}},
        )

    @pytest.mark.asyncio
    async def test_dense_search_no_filter_without_domains(self, service):
        """domains가 없으면 Dense 검색에 filter_dict가 전달되지 않는지 확인."""
        await service.search("테스트", top_k=5)
        service._vector_store.search_records.assert_called_once_with(
            "certificates", "테스트", 15, filter_dict=None
        )

    @pytest.mark.asyncio
    async def test_dense_search_no_filter_with_empty_domains(self, service):
        """domains가 빈 리스트면 filter_dict가 전달되지 않는지 확인."""
        await service.search("테스트", top_k=5, domains=[])
        service._vector_store.search_records.assert_called_once_with(
            "certificates", "테스트", 15, filter_dict=None
        )
