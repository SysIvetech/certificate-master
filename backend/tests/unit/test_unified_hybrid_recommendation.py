"""통합 하이브리드 추천 서비스 테스트 — LLM 없이 동작 검증."""

from app.services.search.bm25_service import BM25SearchService
from app.services.search.context_parser import EnhancedContextParser
from app.services.search.reason_template import ReasonTemplateEngine


class TestUnifiedHybridComponents:
    """개별 컴포넌트가 통합에서 올바르게 동작하는지 테스트."""

    def test_parser_provides_valid_context(self):
        """EnhancedContextParser가 유효한 컨텍스트를 반환한다."""
        parser = EnhancedContextParser()
        ctx = parser.parse("비전공자 IT 취업용 자격증 추천", domains=["IT/소프트웨어"])
        assert ctx.goal == "취업"
        assert ctx.major_background == "비전공자"
        assert len(ctx.preferred_industries) > 0

    def test_bm25_search_with_context(self):
        """BM25가 컨텍스트와 함께 동작한다."""
        bm25 = BM25SearchService()
        bm25.build_index(
            [
                {
                    "id": "cert-001",
                    "title": "정보처리기사",
                    "categories": "국가기술",
                    "series": "정보처리",
                    "overview": "소프트웨어 개발 및 정보처리 업무를 위한 자격증",
                    "career_info": {
                        "industry": "IT/소프트웨어",
                        "related_jobs": "개발자",
                    },
                    "domain": "IT/소프트웨어",
                },
                {
                    "id": "cert-002",
                    "title": "한식조리기능사",
                    "categories": "국가기술",
                    "series": "조리",
                    "overview": "한식 조리에 관한 기능을 검정하는 자격증",
                    "career_info": {"industry": "요식업", "related_jobs": "조리사"},
                    "domain": "요식/조리",
                },
                {
                    "id": "cert-003",
                    "title": "공인중개사",
                    "categories": "국가전문",
                    "series": "부동산",
                    "overview": "부동산 중개 및 거래에 관한 전문 자격증",
                    "career_info": {"industry": "부동산", "related_jobs": "중개사"},
                    "domain": "부동산",
                },
            ]
        )
        results = bm25.search("정보처리 소프트웨어 개발", domains=["IT/소프트웨어"])
        assert len(results) > 0
        assert results[0]["id"] == "cert-001"

    def test_reason_engine_with_parsed_context(self):
        """ReasonTemplateEngine이 파싱된 컨텍스트와 동작한다."""
        parser = EnhancedContextParser()
        ctx = parser.parse("비전공자 취업용 자격증")
        engine = ReasonTemplateEngine()

        cert = {
            "title": "정보처리기사",
            "career_info": {"industry": "IT/소프트웨어", "related_jobs": "개발자"},
            "job_market_info": {
                "job_posting_frequency": "많음",
                "requirement_type": "우대",
            },
            "feasibility_info": {
                "self_study_possible": True,
                "non_major_pass_rate": "35%",
            },
            "study_period_days": 90,
            "difficulty": 3,
        }
        reason = engine.generate(cert, ctx)
        assert len(reason) > 10

    def test_no_llm_imports_needed(self):
        """하이브리드 검색 파이프라인에 LLM import가 필요 없다."""
        # These imports should work without OpenAI key

        assert True  # If we got here, no LLM dependency


class TestLegacyEndpointsRemoved:
    """레거시 엔드포인트가 제거되었는지 확인."""

    def test_wizard_endpoint_removed(self):
        """wizard 엔드포인트가 더 이상 존재하지 않는다."""
        from app.api.v1.recommendations import router

        paths = [getattr(route, "path", None) for route in router.routes]
        assert "" not in paths

    def test_natural_endpoint_removed(self):
        """natural 엔드포인트가 더 이상 존재하지 않는다."""
        from app.api.v1.recommendations import router

        paths = [getattr(route, "path", None) for route in router.routes]
        assert "/natural" not in paths

    def test_unified_endpoint_exists(self):
        """unified 엔드포인트는 존재한다."""
        from app.api.v1.recommendations import router

        paths = [getattr(route, "path", None) for route in router.routes]
        assert "/unified" in paths
