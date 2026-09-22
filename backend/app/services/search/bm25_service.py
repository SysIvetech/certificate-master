"""BM25 키워드 기반 검색 서비스."""

from __future__ import annotations

import logging
from typing import Optional

from rank_bm25 import BM25Okapi

from app.services.search.tokenizer import tokenize
from app.utils.certificate_formatter import build_contextual_prefix

logger = logging.getLogger(__name__)


class BM25SearchService:
    """BM25 기반 키워드 검색 서비스."""

    def __init__(self) -> None:
        self._index: Optional[BM25Okapi] = None
        self._cert_ids: list[str] = []
        self._cert_domains: list[str] = []

    def is_ready(self) -> bool:
        """인덱스가 빌드되었는지 확인한다."""
        return self._index is not None

    def build_index(self, certificates: list[dict]) -> None:
        """자격증 데이터로 BM25 인덱스를 빌드한다."""
        corpus: list[list[str]] = []
        self._cert_ids = []
        self._cert_domains = []

        for cert in certificates:
            text = self._build_index_text(cert)
            tokens = tokenize(text)
            corpus.append(tokens)
            self._cert_ids.append(cert["id"])
            self._cert_domains.append(cert.get("domain", ""))

        if corpus:
            self._index = BM25Okapi(corpus)
        else:
            self._index = None

        logger.info("BM25 인덱스 빌드 완료: %d건", len(corpus))

    def search(
        self,
        query: str,
        top_k: int = 10,
        domains: Optional[list[str]] = None,
    ) -> list[dict]:
        """BM25 키워드 검색을 수행한다."""
        if not self.is_ready():
            raise RuntimeError("BM25 인덱스가 빌드되지 않았습니다.")

        query = query.strip()
        if not query:
            return []

        query_tokens = tokenize(query)
        scores = self._index.get_scores(query_tokens)

        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)

        results: list[dict] = []
        for idx, score in indexed_scores:
            if score <= 0:
                continue
            cert_domain = self._cert_domains[idx]
            if domains and cert_domain not in domains:
                continue
            results.append(
                {
                    "id": self._cert_ids[idx],
                    "score": float(score),
                    "domain": cert_domain,
                }
            )
            if len(results) >= top_k:
                break

        return results

    def _build_index_text(self, cert: dict) -> str:
        """자격증 데이터에서 인덱스용 텍스트를 생성한다.

        Contextual Prefix를 포함하여 키워드 매칭 품질을 향상시킵니다.
        """
        prefix = build_contextual_prefix(cert)
        career_info = cert.get("career_info", {}) or {}
        industry = career_info.get("industry", "")
        related_jobs = career_info.get("related_jobs", "")

        # categories: list[dict] → 이름만 추출
        categories = cert.get("categories", [])
        if isinstance(categories, list):
            categories_str = " ".join(
                cat.get("name", "") if isinstance(cat, dict) else str(cat)
                for cat in categories
            )
        else:
            categories_str = str(categories) if categories else ""

        parts = [
            prefix,
            cert.get("title", ""),
            categories_str,
            cert.get("series", ""),
            " ".join(industry) if isinstance(industry, list) else str(industry or ""),
            (
                " ".join(related_jobs)
                if isinstance(related_jobs, list)
                else str(related_jobs or "")
            ),
            # BM25 키워드 검색에는 overview가 유용 (Dense와 달리 의미 희석 없음)
            (cert.get("overview", "") or "")[:200],
        ]
        return " ".join(filter(None, parts))


_bm25_service: Optional[BM25SearchService] = None


def get_bm25_service() -> BM25SearchService:
    """BM25SearchService 싱글톤 인스턴스를 반환한다."""
    global _bm25_service
    if _bm25_service is None:
        _bm25_service = BM25SearchService()
    return _bm25_service
