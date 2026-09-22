"""BM25 Contextual Prefix 적용 테스트."""

from app.services.search.bm25_service import BM25SearchService


def _make_cert(**overrides):
    base = {
        "id": "cert-001",
        "title": "정보처리기사",
        "series": "기사",
        "domain": "IT",
        "categories": "국가기술자격",
        "difficulty": 3,
        "study_period_days": 90,
        "career_info": {"industry": ["IT", "소프트웨어"], "related_jobs": ["개발자"]},
        "job_market_info": {"job_posting_frequency": "많음"},
        "feasibility_info": {"self_study_possible": True},
        "overview": "정보처리기사 개요",
    }
    base.update(overrides)
    return base


class TestBM25ContextualIndex:

    def test_index_text_contains_prefix_keywords(self):
        svc = BM25SearchService()
        cert = _make_cert()
        text = svc._build_index_text(cert)
        # Contextual Prefix should add "적합" and similar keywords
        assert "적합" in text or "비전공자" in text
        assert "IT" in text

    def test_index_text_still_contains_title(self):
        svc = BM25SearchService()
        cert = _make_cert()
        text = svc._build_index_text(cert)
        assert "정보처리기사" in text

    def test_search_matches_contextual_query(self):
        svc = BM25SearchService()
        # 충분한 문서 수를 사용하여 BM25 IDF가 의미 있는 양수 점수를 산출하도록 함
        certs = [
            _make_cert(id="cert-001", title="정보처리기사"),
            _make_cert(
                id="cert-002",
                title="미용사",
                career_info={"industry": ["미용"], "related_jobs": ["미용사"]},
                job_market_info={"job_posting_frequency": "보통"},
                feasibility_info={},
                domain="서비스",
                overview="미용 기술 자격",
            ),
            _make_cert(
                id="cert-003",
                title="한식조리기능사",
                career_info={"industry": ["요식업"], "related_jobs": ["조리사"]},
                job_market_info={"job_posting_frequency": "보통"},
                feasibility_info={},
                domain="서비스",
                overview="한식 조리 자격",
            ),
            _make_cert(
                id="cert-004",
                title="공인중개사",
                career_info={"industry": ["부동산"], "related_jobs": ["중개사"]},
                job_market_info={"job_posting_frequency": "보통"},
                feasibility_info={},
                domain="부동산",
                overview="부동산 중개 자격",
            ),
            _make_cert(
                id="cert-005",
                title="사회복지사",
                career_info={"industry": ["복지"], "related_jobs": ["복지사"]},
                job_market_info={"job_posting_frequency": "보통"},
                feasibility_info={},
                domain="복지",
                overview="사회복지 자격",
            ),
        ]
        svc.build_index(certs)

        # Query that matches Contextual Prefix vocabulary
        results = svc.search("IT 분야 비전공자에게 적합한 자격증", top_k=5)
        assert len(results) >= 1
        assert results[0]["id"] == "cert-001"
