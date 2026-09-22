"""BM25 키워드 기반 검색 서비스 테스트."""

import pytest

from app.services.search.bm25_service import BM25SearchService


@pytest.fixture
def sample_certificates() -> list[dict]:
    """BM25 테스트용 샘플 자격증 데이터.

    Contextual Prefix 적용 이후 BM25 IDF가 소규모 코퍼스에서도
    양수 점수를 산출하도록 충분한 문서 수(5개 이상)를 확보합니다.
    """
    return [
        {
            "id": "cert-001",
            "title": "정보처리기사",
            "categories": "국가기술자격",
            "series": "정보처리",
            "overview": "소프트웨어 개발 및 운용에 관한 전문 자격증",
            "career_info": {
                "industry": "IT/소프트웨어",
                "related_jobs": "소프트웨어 개발자, 시스템 엔지니어",
            },
            "domain": "IT/소프트웨어",
        },
        {
            "id": "cert-002",
            "title": "전기기사",
            "categories": "국가기술자격",
            "series": "전기",
            "overview": "전기설비의 설계 및 시공에 관한 전문 자격증",
            "career_info": {
                "industry": "전기/전자",
                "related_jobs": "전기 엔지니어, 전기 감리원",
            },
            "domain": "전기/전자",
        },
        {
            "id": "cert-003",
            "title": "정보보안기사",
            "categories": "국가기술자격",
            "series": "정보보안",
            "overview": "정보보안 시스템 운영 및 관리에 관한 전문 자격증",
            "career_info": {
                "industry": "IT/소프트웨어",
                "related_jobs": "보안 전문가, 보안 컨설턴트",
            },
            "domain": "IT/소프트웨어",
        },
        {
            "id": "cert-004",
            "title": "공인중개사",
            "categories": "국가전문자격",
            "series": "부동산",
            "overview": "부동산 중개 및 거래에 관한 전문 자격증",
            "career_info": {
                "industry": "부동산",
                "related_jobs": "부동산 중개사",
            },
            "domain": "부동산",
        },
        {
            "id": "cert-005",
            "title": "한식조리기능사",
            "categories": "국가기술자격",
            "series": "조리",
            "overview": "한식 조리 기술에 관한 기능사 자격증",
            "career_info": {
                "industry": "요식업",
                "related_jobs": "조리사, 셰프",
            },
            "domain": "요식업",
        },
        {
            "id": "cert-006",
            "title": "사회복지사",
            "categories": "국가전문자격",
            "series": "복지",
            "overview": "사회복지 서비스 제공에 관한 전문 자격증",
            "career_info": {
                "industry": "사회복지",
                "related_jobs": "사회복지사, 상담사",
            },
            "domain": "사회복지",
        },
    ]


class TestBM25SearchService:
    def test_build_index(self, sample_certificates):
        service = BM25SearchService()
        service.build_index(sample_certificates)
        assert service.is_ready()

    def test_search_returns_relevant_results(self, sample_certificates):
        service = BM25SearchService()
        service.build_index(sample_certificates)
        results = service.search("정보처리기사", top_k=3)
        assert len(results) > 0
        assert results[0]["id"] == "cert-001"

    def test_search_with_domain_filter(self, sample_certificates):
        service = BM25SearchService()
        service.build_index(sample_certificates)
        results = service.search("기사", domains=["IT/소프트웨어"], top_k=3)
        for r in results:
            assert r["domain"] == "IT/소프트웨어"

    def test_search_returns_scores(self, sample_certificates):
        service = BM25SearchService()
        service.build_index(sample_certificates)
        results = service.search("정보처리", top_k=3)
        assert all("score" in r for r in results)
        assert all(r["score"] >= 0 for r in results)

    def test_search_results_sorted_by_score(self, sample_certificates):
        service = BM25SearchService()
        service.build_index(sample_certificates)
        results = service.search("정보 소프트웨어", top_k=3)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_search_empty_query_returns_empty(self, sample_certificates):
        service = BM25SearchService()
        service.build_index(sample_certificates)
        results = service.search("", top_k=3)
        assert results == []

    def test_search_before_build_raises(self):
        service = BM25SearchService()
        with pytest.raises(RuntimeError):
            service.search("정보처리기사")

    def test_top_k_limits_results(self, sample_certificates):
        service = BM25SearchService()
        service.build_index(sample_certificates)
        results = service.search("기사", top_k=1)
        assert len(results) <= 1

    def test_search_keyword_in_overview(self, sample_certificates):
        service = BM25SearchService()
        service.build_index(sample_certificates)
        results = service.search("보안 시스템", top_k=3)
        ids = [r["id"] for r in results]
        assert "cert-003" in ids
