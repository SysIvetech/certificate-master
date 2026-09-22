"""Contextual Prefix 생성 함수 테스트."""

from app.utils.certificate_formatter import build_contextual_prefix


def _make_cert(**overrides) -> dict:
    """테스트용 자격증 데이터를 생성합니다."""
    base = {
        "title": "정보처리기사",
        "series": "기사",
        "domain": "IT",
        "difficulty": 3,
        "study_period_days": 90,
        "career_info": {
            "industry": ["IT", "소프트웨어"],
            "related_jobs": ["소프트웨어개발자"],
        },
        "job_market_info": {
            "job_posting_frequency": "많음",
            "requirement_type": "우대",
        },
        "feasibility_info": {
            "self_study_possible": True,
        },
    }
    base.update(overrides)
    return base


class TestBuildContextualPrefix:

    def test_returns_string(self):
        cert = _make_cert()
        result = build_contextual_prefix(cert)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_includes_domain(self):
        cert = _make_cert()
        result = build_contextual_prefix(cert)
        assert "IT" in result

    def test_includes_series(self):
        cert = _make_cert()
        result = build_contextual_prefix(cert)
        assert "기사" in result

    def test_non_major_friendly_target(self):
        cert = _make_cert(
            feasibility_info={"self_study_possible": True},
            difficulty=2,
        )
        result = build_contextual_prefix(cert)
        assert "비전공자" in result

    def test_employment_purpose_when_high_demand(self):
        cert = _make_cert(
            job_market_info={
                "job_posting_frequency": "매우 많음",
                "requirement_type": "우대",
            },
        )
        result = build_contextual_prefix(cert)
        assert "취업" in result or "이직" in result

    def test_required_purpose(self):
        cert = _make_cert(
            job_market_info={
                "requirement_type": "필수",
                "job_posting_frequency": "많음",
            },
        )
        result = build_contextual_prefix(cert)
        assert "필수" in result

    def test_period_in_months(self):
        cert = _make_cert(study_period_days=180)
        result = build_contextual_prefix(cert)
        assert "6개월" in result

    def test_period_in_days_when_short(self):
        cert = _make_cert(study_period_days=14)
        result = build_contextual_prefix(cert)
        assert "14일" in result

    def test_difficulty_included(self):
        cert = _make_cert(difficulty=4)
        result = build_contextual_prefix(cert)
        assert "4/5" in result

    def test_empty_fields_handled_gracefully(self):
        cert = {
            "title": "테스트",
            "series": "",
            "domain": "",
            "difficulty": None,
            "study_period_days": None,
            "career_info": {},
            "job_market_info": {},
            "feasibility_info": {},
        }
        result = build_contextual_prefix(cert)
        assert isinstance(result, str)
