"""하이브리드 검색 서비스: Dense(ChromaDB) + Sparse(BM25) + RRF 결합."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from app.services.search.bm25_service import BM25SearchService

logger = logging.getLogger(__name__)


class HybridSearchService:
    """Dense 벡터 검색과 Sparse BM25 검색을 RRF로 결합하는 하이브리드 검색 서비스."""

    RRF_K = 60

    def __init__(self, vector_store, bm25_service: BM25SearchService) -> None:
        self._vector_store = vector_store
        self._bm25_service = bm25_service
        self.last_search_stats: dict = {}

    async def search(
        self,
        query: str,
        top_k: int = 10,
        domains: Optional[list[str]] = None,
        dense_weight: float = 1.0,
        sparse_weight: float = 1.0,
        filter_dict: Optional[dict] = None,
    ) -> list[dict]:
        """Dense + Sparse 검색 결과를 RRF(Reciprocal Rank Fusion)로 결합하여 반환한다.

        Args:
            query: 검색 쿼리 문자열.
            top_k: 반환할 최대 결과 수.
            domains: 필터링할 도메인 목록 (선택).
            dense_weight: Dense 검색 RRF 가중치.
            sparse_weight: Sparse 검색 RRF 가중치.
            filter_dict: ChromaDB 메타데이터 필터 (선택). 도메인 필터와 병합됩니다.

        Returns:
            RRF 점수 기준으로 정렬된 검색 결과 리스트.
        """
        start = time.monotonic()
        retrieve_k = top_k * 3

        # Dense 검색용 필터 구성: 도메인 필터 + 메타데이터 필터 병합
        dense_filter = None
        domain_filter = {"domain": {"$in": domains}} if domains else None

        if domain_filter and filter_dict:
            dense_filter = {"$and": [domain_filter, filter_dict]}
        elif domain_filter:
            dense_filter = domain_filter
        elif filter_dict:
            dense_filter = filter_dict

        # Dense(벡터) 검색과 Sparse(BM25) 검색을 병렬 실행
        # search_records / bm25.search 모두 동기 함수이므로 to_thread로 감싸기
        dense_results, sparse_results = await asyncio.gather(
            asyncio.to_thread(
                self._vector_store.search_records,
                self._vector_store.NAMESPACE,
                query,
                retrieve_k,
                filter_dict=dense_filter,
            ),
            asyncio.to_thread(
                self._bm25_service.search,
                query,
                retrieve_k,
                domains,
            ),
        )

        # RRF 점수 계산: score = weight / (K + rank), rank는 1-based
        rrf_scores: dict[str, float] = {}

        for rank, result in enumerate(dense_results, 1):
            rrf_scores[result["id"]] = dense_weight / (self.RRF_K + rank)

        for rank, result in enumerate(sparse_results, 1):
            cert_id = result["id"]
            rrf_scores.setdefault(cert_id, 0.0)
            rrf_scores[cert_id] += sparse_weight / (self.RRF_K + rank)

        # RRF 점수 내림차순 정렬 후 top_k 제한
        sorted_results = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[
            :top_k
        ]

        elapsed = (time.monotonic() - start) * 1000

        self.last_search_stats = {
            "dense_count": len(dense_results),
            "sparse_count": len(sparse_results),
            "merged_count": len(sorted_results),
            "elapsed_ms": round(elapsed, 2),
        }

        logger.info(
            "하이브리드 검색 완료: query=%r, dense=%d, sparse=%d, merged=%d, elapsed=%.1fms",
            query,
            len(dense_results),
            len(sparse_results),
            len(sorted_results),
            elapsed,
        )

        return [
            {"id": cert_id, "rrf_score": score} for cert_id, score in sorted_results
        ]
