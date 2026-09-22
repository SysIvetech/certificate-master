"""difficulty와 study_period_days 정합성 검증 테스트."""

import pytest

from app.services.llm.service import (
    CertificateEnrichment,
    Phase1Extraction,
)

# 난이도별 허용 study_period_days 범위 (프롬프트 난이도 기준과 일치)
DIFFICULTY_PERIOD_RANGES = {
    1: (1, 21),  # 1~3주
    2: (14, 90),  # 2주~3개월
    3: (60, 210),  # 2~7개월
    4: (150, 540),  # 5개월~1.5년
    5: (300, 1095),  # 10개월~3년
}


def _make_phase1_data(**overrides) -> dict:
    """Phase1Extraction 생성에 필요한 기본 데이터."""
    base = {
        "overview_draft": "테스트 개요",
        "difficulty": 3,
        "study_period_days": 90,
        "exam_info": {
            "subjects": [],
            "exam_type": "필기",
            "passing_criteria": "60점",
            "total_fee": None,
        },
        "career_info": {
            "use_cases": [],
            "related_jobs": [],
            "average_salary": None,
            "job_prospects": None,
        },
        "user_reviews": {
            "summary": "후기",
            "difficulty_feedback": "보통",
            "study_tips": [],
        },
        "study_guide": {
            "study_methods": [],
            "recommended_books": [],
        },
        "official_sources": {
            "official_site": None,
            "issuing_organization": None,
        },
        "lectures": [],
    }
    base.update(overrides)
    return base


def _make_enrichment_data(**overrides) -> dict:
    """CertificateEnrichment 생성에 필요한 기본 데이터."""
    base = {
        "overview": "정제된 개요입니다.",
        "difficulty": 3,
        "study_period_days": 90,
        "exam_info": {},
        "career_info": {},
        "user_reviews": {},
        "study_guide": {},
        "official_sources": {},
    }
    base.update(overrides)
    return base


class TestDifficultyPeriodConsistency:
    """difficulty와 study_period_days 간 정합성 검증."""

    @pytest.mark.parametrize(
        "difficulty, study_days",
        [
            (1, 7),  # 난이도1, 1주 -> OK
            (1, 14),  # 난이도1, 2주 -> OK
            (2, 30),  # 난이도2, 1개월 -> OK
            (2, 60),  # 난이도2, 2개월 -> OK
            (3, 90),  # 난이도3, 3개월 -> OK
            (3, 180),  # 난이도3, 6개월 -> OK
            (4, 200),  # 난이도4, ~7개월 -> OK
            (4, 365),  # 난이도4, 1년 -> OK
            (5, 365),  # 난이도5, 1년 -> OK
            (5, 730),  # 난이도5, 2년 -> OK
        ],
    )
    def test_consistent_values_pass_through_unchanged(self, difficulty, study_days):
        """정합성이 맞는 값은 그대로 유지된다."""
        data = _make_phase1_data(difficulty=difficulty, study_period_days=study_days)
        result = Phase1Extraction(**data)
        assert result.difficulty == difficulty
        assert result.study_period_days == study_days

    @pytest.mark.parametrize(
        "difficulty, study_days, expected_min, expected_max",
        [
            # 난이도 4인데 2일 -> 범위 150~540으로 클램핑
            (4, 2, 150, 540),
            # 난이도 1인데 365일 -> 범위 1~21로 클램핑
            (1, 365, 1, 21),
            # 난이도 3인데 1일 -> 범위 60~210으로 클램핑
            (3, 1, 60, 210),
            # 난이도 5인데 30일 -> 범위 300~1095으로 클램핑
            (5, 30, 300, 1095),
            # 난이도 2인데 500일 -> 범위 14~90으로 클램핑
            (2, 500, 14, 90),
        ],
    )
    def test_inconsistent_values_are_clamped(
        self, difficulty, study_days, expected_min, expected_max
    ):
        """비일관 값은 난이도 기준 범위로 클램핑된다."""
        data = _make_phase1_data(difficulty=difficulty, study_period_days=study_days)
        result = Phase1Extraction(**data)
        assert result.difficulty == difficulty
        assert expected_min <= result.study_period_days <= expected_max

    def test_study_period_days_upper_bound(self):
        """study_period_days가 1095(3년)을 초과하면 클램핑된다."""
        data = _make_phase1_data(difficulty=5, study_period_days=2000)
        result = Phase1Extraction(**data)
        assert result.study_period_days <= 1095

    def test_enrichment_also_validates_consistency(self):
        """CertificateEnrichment도 동일한 정합성 검증을 수행한다."""
        data = _make_enrichment_data(difficulty=4, study_period_days=2)
        result = CertificateEnrichment(**data)
        # 난이도4 범위: 150~540
        assert 150 <= result.study_period_days <= 540

    def test_enrichment_consistent_values_unchanged(self):
        """CertificateEnrichment에서 정합성 맞는 값은 변경 없음."""
        data = _make_enrichment_data(difficulty=3, study_period_days=120)
        result = CertificateEnrichment(**data)
        assert result.difficulty == 3
        assert result.study_period_days == 120

    def test_none_difficulty_defaults_and_validates(self):
        """difficulty=None이면 기본값 3으로 설정 후 정합성 검증."""
        data = _make_phase1_data(difficulty=None, study_period_days=90)
        result = Phase1Extraction(**data)
        assert result.difficulty == 3
        assert 60 <= result.study_period_days <= 210

    def test_none_study_period_defaults_and_validates(self):
        """study_period_days=None이면 기본값 90으로 설정 후 정합성 검증."""
        data = _make_phase1_data(difficulty=3, study_period_days=None)
        result = Phase1Extraction(**data)
        assert result.study_period_days == 90
        assert result.difficulty == 3
