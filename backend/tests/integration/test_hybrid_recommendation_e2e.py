# backend/tests/integration/test_hybrid_recommendation_e2e.py
"""하이브리드 추천 시스템 E2E 통합 테스트.

전체 파이프라인: 파서 → BM25 → 이유 생성, LLM 의존성 없음.
"""

import pytest

from app.services.search.bm25_service import BM25SearchService
from app.services.search.context_parser import EnhancedContextParser
from app.services.search.reason_template import ReasonTemplateEngine
from app.services.search.tokenizer import tokenize


@pytest.fixture
def sample_certs():
    return [
        {
            "id": "cert-001",
            "title": "정보처리기사",
            "categories": "국가기술자격",
            "series": "정보처리",
            "overview": "소프트웨어 개발 및 운용 전문 자격증",
            "career_info": {
                "industry": "IT/소프트웨어",
                "related_jobs": "소프트웨어 개발자, 시스템 엔지니어",
            },
            "job_market_info": {
                "job_posting_frequency": "많음",
                "preferred_industries": "IT, 금융",
                "requirement_type": "우대",
            },
            "feasibility_info": {
                "self_study_possible": True,
                "non_major_pass_rate": "35%",
            },
            "study_period_days": 90,
            "difficulty": 3,
            "domain": "IT/소프트웨어",
        },
        {
            "id": "cert-002",
            "title": "전기기사",
            "categories": "국가기술자격",
            "series": "전기",
            "overview": "전기설비 설계 및 시공 전문 자격증",
            "career_info": {
                "industry": "전기/전자",
                "related_jobs": "전기 엔지니어",
            },
            "job_market_info": {"job_posting_frequency": "보통"},
            "feasibility_info": {"self_study_possible": False},
            "study_period_days": 180,
            "difficulty": 4,
            "domain": "전기/전자",
        },
        {
            "id": "cert-003",
            "title": "한식조리기능사",
            "categories": "국가기술자격",
            "series": "조리",
            "overview": "한식 조리 전문 자격증",
            "career_info": {
                "industry": "식품/조리",
                "related_jobs": "조리사, 셰프",
            },
            "job_market_info": {"job_posting_frequency": "보통"},
            "feasibility_info": {"self_study_possible": True},
            "study_period_days": 60,
            "difficulty": 2,
            "domain": "식품/조리",
        },
        {
            "id": "cert-004",
            "title": "공인회계사",
            "categories": "국가전문자격",
            "series": "회계",
            "overview": "회계 및 감사 전문 자격증",
            "career_info": {
                "industry": "금융/회계",
                "related_jobs": "회계사, 감사",
            },
            "job_market_info": {"job_posting_frequency": "많음"},
            "feasibility_info": {"self_study_possible": False},
            "study_period_days": 365,
            "difficulty": 5,
            "domain": "금융/회계",
        },
    ]


class TestE2EPipeline:
    def test_context_parser_to_bm25(self, sample_certs):
        """파싱 → BM25 검색 흐름."""
        parser = EnhancedContextParser()
        ctx = parser.parse("비전공자 IT 취업 자격증 추천")
        assert ctx.goal == "취업"

        bm25 = BM25SearchService()
        bm25.build_index(sample_certs)
        results = bm25.search(
            "IT 소프트웨어 자격증", domains=["IT/소프트웨어"], top_k=5
        )
        assert len(results) > 0
        assert results[0]["id"] == "cert-001"

    def test_bm25_to_reason_template(self, sample_certs):
        """BM25 검색 → 이유 생성 흐름."""
        parser = EnhancedContextParser()
        ctx = parser.parse("비전공자 취업용 IT 자격증")

        bm25 = BM25SearchService()
        bm25.build_index(sample_certs)
        bm25.search("IT 자격증", top_k=5)

        engine = ReasonTemplateEngine()
        cert = sample_certs[0]
        reason = engine.generate(cert, ctx)
        assert len(reason) > 0
        assert any(k in reason for k in ["비전공", "독학", "IT", "채용"])

    def test_full_pipeline_no_llm(self, sample_certs):
        """전체 파이프라인이 LLM 없이 동작한다."""
        parser = EnhancedContextParser()
        ctx = parser.parse(
            "3개월 안에 딸 수 있는 쉬운 IT 자격증", domains=["IT/소프트웨어"]
        )

        bm25 = BM25SearchService()
        bm25.build_index(sample_certs)
        results = bm25.search("IT 소프트웨어", top_k=5)

        engine = ReasonTemplateEngine()
        for r in results:
            cert = next(c for c in sample_certs if c["id"] == r["id"])
            reason = engine.generate(cert, ctx)
            assert len(reason) > 0

    def test_tokenizer_handles_cert_titles(self, sample_certs):
        """토큰화가 자격증 제목을 잘 처리한다."""
        for cert in sample_certs:
            tokens = tokenize(cert["title"])
            assert len(tokens) > 0
            assert cert["title"] in tokens

    def test_domain_filtering_end_to_end(self, sample_certs):
        """도메인 필터링이 전체 파이프라인에서 동작한다."""
        bm25 = BM25SearchService()
        bm25.build_index(sample_certs)

        # IT 도메인만 검색
        results = bm25.search("기사", domains=["IT/소프트웨어"], top_k=5)
        for r in results:
            assert r["domain"] == "IT/소프트웨어"

        # 전기 도메인만 검색
        results = bm25.search("기사", domains=["전기/전자"], top_k=5)
        for r in results:
            assert r["domain"] == "전기/전자"

    def test_numeric_context_flows_through(self, sample_certs):
        """수치 파싱이 전체 파이프라인에서 반영된다."""
        parser = EnhancedContextParser()
        ctx = parser.parse("하루 2시간, 6개월 안에 준비하고 싶어요")
        assert ctx.weekly_study_hours == 14
        assert ctx.max_study_period_days == 180

        engine = ReasonTemplateEngine()
        reason = engine.generate(sample_certs[0], ctx)
        assert len(reason) > 0
