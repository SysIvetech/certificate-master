"""Contextual 임베딩 텍스트 생성 함수 테스트."""

from app.utils.certificate_formatter import (
    build_contextual_prefix,
    format_contextual_search_text,
)


def _make_cert(**overrides) -> dict:
    base = {
        "title": "정보처리기사",
        "series": "기사",
        "domain": "IT",
        "difficulty": 3,
        "study_period_days": 90,
        "categories": [{"code": "01", "name": "국가기술자격"}],
        "overview": "정보처리기사는 IT 분야의 대표적인 국가기술자격입니다." * 5,
        "career_info": {
            "industry": ["IT", "소프트웨어"],
            "related_jobs": ["소프트웨어개발자", "시스템분석사"],
            "use_cases": ["웹개발", "모바일개발"],
        },
        "job_market_info": {
            "job_posting_frequency": "많음",
            "preferred_industries": ["IT기업", "금융업"],
        },
        "feasibility_info": {"self_study_possible": True},
    }
    base.update(overrides)
    return base


class TestFormatContextualSearchText:

    def test_starts_with_contextual_prefix(self):
        cert = _make_cert()
        result = format_contextual_search_text(cert)
        prefix = build_contextual_prefix(cert)
        assert result.startswith(prefix)

    def test_includes_title(self):
        cert = _make_cert()
        result = format_contextual_search_text(cert)
        assert "정보처리기사" in result

    def test_includes_industry(self):
        cert = _make_cert()
        result = format_contextual_search_text(cert)
        assert "소프트웨어" in result

    def test_includes_related_jobs(self):
        cert = _make_cert()
        result = format_contextual_search_text(cert)
        assert "소프트웨어개발자" in result

    def test_does_not_include_long_overview(self):
        """overview가 통째로 포함되지 않는지 확인 (신호 희석 방지)."""
        cert = _make_cert()
        result = format_contextual_search_text(cert)
        assert cert["overview"] not in result

    def test_includes_matching_tags_for_self_study(self):
        cert = _make_cert(feasibility_info={"self_study_possible": True})
        result = format_contextual_search_text(cert)
        assert "독학가능" in result or "비전공자추천" in result

    def test_includes_categories(self):
        cert = _make_cert()
        result = format_contextual_search_text(cert)
        assert "국가기술자격" in result

    def test_includes_use_cases(self):
        cert = _make_cert()
        result = format_contextual_search_text(cert)
        assert "웹개발" in result

    def test_includes_preferred_industries(self):
        cert = _make_cert()
        result = format_contextual_search_text(cert)
        assert "IT기업" in result

    def test_empty_cert_handled(self):
        cert = {
            "title": "테스트",
            "series": "",
            "domain": "",
            "difficulty": None,
            "study_period_days": None,
            "categories": [],
            "overview": "",
            "career_info": {},
            "job_market_info": {},
            "feasibility_info": {},
        }
        result = format_contextual_search_text(cert)
        assert isinstance(result, str)
        assert len(result) > 0
