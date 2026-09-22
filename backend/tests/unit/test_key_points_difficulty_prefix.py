"""Test key_points difficulty prefix."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.schemas.certificate import Certificate
from app.schemas.recommendation import RecommendationRequest
from app.services.study.recommendation_service import RecommendationService


class TestKeyPointsDifficultyPrefix:
    """key_points 난이도 문구에 '난이도: ' 접두사 테스트."""

    @pytest.fixture
    def mock_db(self):
        """Mock DB session."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db):
        """RecommendationService instance."""
        return RecommendationService(db=mock_db)

    @pytest.fixture
    def sample_request(self):
        """샘플 추천 요청."""
        return RecommendationRequest(
            purpose="취업",
            interest_domains=["IT개발"],
            study_timeline="6개월 이하",
            difficulty_preference="중간",
        )

    @pytest.fixture
    def sample_certificate(self):
        """난이도 3인 샘플 자격증."""
        return Certificate(
            id="test-cert-id",
            raw_id="T_테스트자격증",
            categories=[{"code": "T", "name": "국가기술자격"}],
            series="테스트계열",
            title="테스트자격증",
            difficulty=3,
            study_period_days=90,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def test_key_points_difficulty_starts_with_prefix(
        self, service, sample_certificate, sample_request
    ):
        """key_points의 난이도 문구가 '난이도: '로 시작해야 한다."""
        key_points = service._generate_key_points(sample_certificate, sample_request)

        # 첫 번째 포인트가 난이도 관련 문구
        assert len(key_points) > 0
        difficulty_point = key_points[0]

        # '난이도: '로 시작해야 함
        assert difficulty_point.startswith("난이도: "), (
            f"난이도 문구가 '난이도: '로 시작해야 합니다. "
            f"실제 값: '{difficulty_point}'"
        )

    def test_key_points_difficulty_prefix_for_all_levels(self, service, sample_request):
        """모든 난이도 레벨(1-5)에서 '난이도: ' 접두사가 붙어야 한다."""
        for difficulty_level in [1, 2, 3, 4, 5]:
            cert = Certificate(
                id=f"test-cert-{difficulty_level}",
                raw_id=f"T_테스트자격증{difficulty_level}",
                categories=[{"code": "T", "name": "국가기술자격"}],
                series="테스트계열",
                title=f"테스트자격증{difficulty_level}",
                difficulty=difficulty_level,
                study_period_days=90,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            key_points = service._generate_key_points(cert, sample_request)

            assert len(key_points) > 0
            difficulty_point = key_points[0]
            assert difficulty_point.startswith("난이도: "), (
                f"난이도 {difficulty_level}에서 '난이도: ' 접두사가 없습니다. "
                f"실제 값: '{difficulty_point}'"
            )

    def test_key_points_difficulty_format_example(
        self, service, sample_certificate, sample_request
    ):
        """난이도 3의 경우 '난이도: 중급 난이도로 체계적 학습 필요' 형식이어야 한다."""
        key_points = service._generate_key_points(sample_certificate, sample_request)

        difficulty_point = key_points[0]
        assert difficulty_point == "난이도: 중급 난이도로 체계적 학습 필요", (
            f"예상 값: '난이도: 중급 난이도로 체계적 학습 필요', "
            f"실제 값: '{difficulty_point}'"
        )
