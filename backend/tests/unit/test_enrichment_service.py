"""enrichment_service.py 테스트.

TDD: Supabase → SQLAlchemy 마이그레이션 테스트.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models.certificate import Certificate
from scripts.seed_certificates import get_mariadb_session


# anyio 백엔드 설정 (pytest-asyncio 대신 anyio 사용)
@pytest.fixture
def anyio_backend():
    return "asyncio"


class TestEnrichmentServiceMariaDB:
    """EnrichmentService MariaDB 통합 테스트."""

    def test_enrichment_service_accepts_sqlalchemy_session(self):
        """SQLAlchemy Session을 받아들이는지 테스트."""
        from app.services.enrichment_service import get_enrichment_service

        session = get_mariadb_session()
        try:
            # Session 타입을 받아야 함
            service = get_enrichment_service(session)
            assert service is not None
            # session이 저장되어 있어야 함
            assert hasattr(service, "session")
            assert service.session is session
        finally:
            session.close()

    def test_enrichment_service_has_required_attributes(self):
        """필수 속성들이 있는지 테스트."""
        from app.services.enrichment_service import get_enrichment_service

        session = get_mariadb_session()
        try:
            service = get_enrichment_service(session)
            # 필수 서비스들
            assert hasattr(service, "search")  # brave → search (추상화)
            assert hasattr(service, "llm")
        finally:
            session.close()

    @pytest.mark.anyio
    async def test_enrich_certificate_updates_db_with_sqlalchemy(self, anyio_backend):
        """enrich_certificate가 SQLAlchemy로 DB를 업데이트하는지 테스트."""
        from app.services.enrichment_service import CertificateEnrichmentService

        # Mock session
        mock_session = MagicMock(spec=Session)
        mock_cert = MagicMock(spec=Certificate)
        mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_cert
        )

        # Mock search and llm services
        with (
            patch(
                "app.services.enrichment_service.get_search_service"
            ) as MockGetSearch,
            patch("app.services.enrichment_service.LLMService") as MockLLM,
        ):

            mock_search_instance = MagicMock()
            mock_search_instance.provider_name = "searxng"
            mock_search_instance.search_certificate_comprehensive = AsyncMock(
                return_value={
                    "general": [],
                    "statistics": [],
                    "career": [],
                    "reviews": [],
                    "study_methods": [],
                    "books": [],
                    "lectures": [],
                    "official": [],
                }
            )
            mock_search_instance.format_search_results_for_llm.return_value = (
                "test context"
            )
            MockGetSearch.return_value = mock_search_instance

            mock_llm_instance = MockLLM.return_value
            mock_enrichment = MagicMock()
            mock_enrichment.overview = "Test overview"
            mock_enrichment.difficulty = 3
            mock_enrichment.study_period_days = 90
            mock_enrichment.exam_info = {"subjects": ["과목1"]}
            mock_enrichment.career_info = {"use_cases": ["용도1"]}
            mock_enrichment.user_reviews = {"summary": "Test"}
            mock_enrichment.study_guide = {
                "study_methods": ["방법1"],
                "learning_sequence": ["단계1"],
            }
            mock_enrichment.official_sources = {"official_site": "https://test.com"}
            mock_enrichment.recommended_lectures = []
            mock_enrichment.model_dump.return_value = {}
            mock_llm_instance.enrich_certificate = AsyncMock(
                return_value=mock_enrichment
            )

            service = CertificateEnrichmentService(mock_session)
            result = await service.enrich_certificate("test-id", "테스트 자격증")

            # SQLAlchemy 스타일로 업데이트해야 함
            # session.query().filter().first()가 호출되어야 함
            mock_session.query.assert_called()
            # session.commit()이 호출되어야 함
            mock_session.commit.assert_called()

            assert result["status"] == "success"


class TestCertificateEnrichmentSchema:
    """CertificateEnrichment 스키마 테스트."""

    def test_recommended_lectures_is_optional(self):
        """recommended_lectures 필드는 Optional이어야 함 (덜 유명한 자격증 대비)."""
        from app.services.llm.service import CertificateEnrichment

        # recommended_lectures 없이 생성 가능해야 함
        data = {
            "overview": "농화학기술사는 농업 화학 분야의 전문가 자격증입니다.",
            "difficulty": 4,
            "study_period_days": 180,
            "passing_rate": 15.5,
            "exam_info": {"subjects": ["농업화학"]},
            "career_info": {"use_cases": ["농업연구소"]},
            "user_reviews": {"summary": "어렵다"},
            "study_guide": {"study_methods": ["이론 학습"]},
            "official_sources": {"official_site": "https://q-net.or.kr"},
            # recommended_lectures 없음!
        }

        # ValidationError 없이 생성되어야 함
        enrichment = CertificateEnrichment(**data)
        assert enrichment.recommended_lectures == []  # 기본값 빈 리스트


class TestEnrichmentServiceErrorHandling:
    """에러 처리 테스트."""

    @pytest.mark.anyio
    async def test_enrich_certificate_handles_not_found(self, anyio_backend):
        """자격증을 찾지 못했을 때 에러 처리."""
        from app.services.enrichment_service import CertificateEnrichmentService

        mock_session = MagicMock(spec=Session)
        mock_session.query.return_value.filter.return_value.first.return_value = None

        with (
            patch(
                "app.services.enrichment_service.get_search_service"
            ) as MockGetSearch,
            patch("app.services.enrichment_service.LLMService") as MockLLM,
        ):

            # Mock search service
            mock_search_instance = MagicMock()
            mock_search_instance.provider_name = "searxng"
            mock_search_instance.search_certificate_comprehensive = AsyncMock(
                return_value={
                    "general": [],
                    "statistics": [],
                    "career": [],
                    "reviews": [],
                    "study_methods": [],
                    "books": [],
                    "lectures": [],
                    "official": [],
                }
            )
            mock_search_instance.format_search_results_for_llm.return_value = (
                "test context"
            )
            MockGetSearch.return_value = mock_search_instance

            # Mock LLM
            mock_llm_instance = MockLLM.return_value
            mock_enrichment = MagicMock()
            mock_enrichment.overview = "Test"
            mock_enrichment.difficulty = 3
            mock_enrichment.study_period_days = 90
            mock_enrichment.exam_info = {"subjects": []}
            mock_enrichment.career_info = {"use_cases": []}
            mock_enrichment.user_reviews = {"summary": ""}
            mock_enrichment.study_guide = {"study_methods": [], "learning_sequence": []}
            mock_enrichment.official_sources = {"official_site": ""}
            mock_enrichment.recommended_lectures = []
            mock_llm_instance.enrich_certificate = AsyncMock(
                return_value=mock_enrichment
            )

            service = CertificateEnrichmentService(mock_session)
            result = await service.enrich_certificate("non-existent", "없는 자격증")

            assert result["status"] == "error"
            assert "찾을 수 없습니다" in result["error"]
