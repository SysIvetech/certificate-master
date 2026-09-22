"""검색 최적화 압축 텍스트 (format_search_text) 테스트."""

import pytest

from app.utils.certificate_formatter import format_search_text


@pytest.fixture
def sample_cert():
    """실제 DB 형식과 동일한 테스트 데이터."""
    return {
        "title": "정보처리기사",
        "categories": [{"code": "NCS01", "name": "국가기술자격"}],
        "series": "정보처리",
        "overview": "소프트웨어 개발 및 운용에 관한 전문 자격증으로 "
        + "상세내용 " * 100,
        "career_info": {
            "industry": ["IT/소프트웨어", "금융"],
            "related_jobs": ["소프트웨어 개발자", "시스템 엔지니어", "DBA"],
        },
        "job_market_info": {
            "preferred_industries": ["IT", "금융", "제조"],
        },
    }


class TestFormatSearchText:
    def test_includes_title(self, sample_cert):
        text = format_search_text(sample_cert)
        assert "정보처리기사" in text

    def test_includes_categories(self, sample_cert):
        text = format_search_text(sample_cert)
        assert "국가기술자격" in text

    def test_includes_series(self, sample_cert):
        text = format_search_text(sample_cert)
        assert "정보처리" in text

    def test_includes_industry(self, sample_cert):
        text = format_search_text(sample_cert)
        assert "IT/소프트웨어" in text
        assert "금융" in text

    def test_includes_related_jobs(self, sample_cert):
        text = format_search_text(sample_cert)
        assert "소프트웨어 개발자" in text
        assert "시스템 엔지니어" in text

    def test_includes_preferred_industries(self, sample_cert):
        text = format_search_text(sample_cert)
        assert "IT" in text
        assert "제조" in text

    def test_overview_truncated(self, sample_cert):
        text = format_search_text(sample_cert)
        full_overview = sample_cert["overview"]
        assert full_overview not in text
        assert full_overview[:50] in text

    def test_shorter_than_full_text(self, sample_cert):
        from app.utils.certificate_formatter import format_certificate_text

        search_text = format_search_text(sample_cert)
        full_text = format_certificate_text(sample_cert)
        assert len(search_text) < len(full_text)

    def test_handles_missing_fields(self):
        cert = {"title": "테스트자격증"}
        text = format_search_text(cert)
        assert "테스트자격증" in text

    def test_returns_non_empty(self, sample_cert):
        text = format_search_text(sample_cert)
        assert len(text.strip()) > 0

    def test_handles_string_industry(self):
        """industry가 문자열인 경우도 처리."""
        cert = {
            "title": "테스트",
            "career_info": {"industry": "건설"},
        }
        text = format_search_text(cert)
        assert "건설" in text

    def test_handles_empty_categories(self):
        """categories가 빈 리스트인 경우."""
        cert = {"title": "테스트", "categories": []}
        text = format_search_text(cert)
        assert "테스트" in text
