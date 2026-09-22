"""Unit tests for certificate text formatter utility.

B4: format 함수 중복 제거 - 공통 유틸리티 함수 테스트.
"""


class TestCertificateFormatter:
    """Certificate text formatter 테스트."""

    def test_format_basic_certificate_info(self):
        """기본 자격증 정보 포맷 테스트."""
        from app.utils.certificate_formatter import format_certificate_text

        cert = {
            "title": "정보처리기사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "정보처리",
            "overview": "IT 분야의 대표 자격증",
            "difficulty": 3,
            "study_period_days": 90,
        }

        result = format_certificate_text(cert)

        assert "자격증: 정보처리기사" in result
        assert "분류: 국가기술자격" in result
        assert "계열: 정보처리" in result
        assert "개요: IT 분야의 대표 자격증" in result
        assert "난이도: 3/5" in result
        assert "준비기간: 90일" in result

    def test_format_with_career_info(self):
        """진로 정보 포함 포맷 테스트."""
        from app.utils.certificate_formatter import format_certificate_text

        cert = {
            "title": "정보처리기사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "career_info": {
                "industry": ["IT", "소프트웨어"],
                "use_cases": ["개발", "운영"],
                "related_jobs": ["개발자", "SE"],
                "job_prospects": "매우 좋음",
                "average_salary": "연 5,000만원",
            },
        }

        result = format_certificate_text(cert)

        assert "산업분야: IT, 소프트웨어" in result
        assert "활용분야: 개발, 운영" in result
        assert "관련직업: 개발자, SE" in result
        assert "취업전망: 매우 좋음" in result
        assert "평균연봉: 연 5,000만원" in result

    def test_format_with_exam_info(self):
        """시험 정보 포함 포맷 테스트."""
        from app.utils.certificate_formatter import format_certificate_text

        cert = {
            "title": "정보처리기사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "exam_info": {
                "exam_type": "필기+실기",
                "subjects": ["소프트웨어설계", "데이터베이스"],
                "passing_criteria": "60점 이상",
            },
        }

        result = format_certificate_text(cert)

        assert "시험유형: 필기+실기" in result
        assert "시험과목: 소프트웨어설계, 데이터베이스" in result
        assert "합격기준: 60점 이상" in result

    def test_format_with_exam_info_subjects_as_dict_list(self):
        """시험 과목이 딕셔너리 리스트일 때 포맷 테스트.

        일부 자격증(예: 그래픽표준기술사)의 subjects 필드가
        문자열 리스트가 아닌 딕셔너리 리스트로 저장되어 있음.
        예: [{'name': '그래픽표준 인쇄기술', 'questions': None, 'time': None}]
        """
        from app.utils.certificate_formatter import format_certificate_text

        cert = {
            "title": "그래픽표준기술사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "exam_info": {
                "exam_type": "면접시험",
                "subjects": [
                    {"name": "그래픽표준 인쇄기술", "questions": None, "time": None},
                    {"name": "인쇄공정관리", "questions": 20, "time": 60},
                ],
                "passing_criteria": "60점 이상",
            },
        }

        result = format_certificate_text(cert)

        # 오류 없이 텍스트가 생성되어야 함
        assert "그래픽표준기술사" in result
        # subjects 이름이 포함되어야 함
        assert "그래픽표준 인쇄기술" in result
        assert "인쇄공정관리" in result

    def test_format_with_empty_optional_fields(self):
        """선택 필드가 비어있을 때 처리 테스트."""
        from app.utils.certificate_formatter import format_certificate_text

        cert = {
            "title": "테스트 자격증",
            "categories": [{"code": "T", "name": "테스트"}],
            "career_info": None,
            "exam_info": {},
            "user_reviews": None,
            "study_guide": {},
        }

        result = format_certificate_text(cert)

        # 기본 정보는 포함
        assert "자격증: 테스트 자격증" in result
        # 빈 선택 필드는 에러 없이 처리
        assert result is not None

    def test_format_builds_metadata(self):
        """메타데이터 빌드 테스트."""
        from app.utils.certificate_formatter import build_certificate_metadata

        cert = {
            "id": "cert-123",
            "title": "정보처리기사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "정보처리",
            "difficulty": 3,
            "study_period_days": 90,
            "overview": "IT 분야의 대표 자격증입니다.",
            "career_info": {
                "industry": ["IT", "소프트웨어"],
                "average_salary": "연 5,000만원",
            },
            "exam_info": {
                "exam_type": "필기+실기",
            },
        }

        metadata = build_certificate_metadata(cert)

        assert metadata["title"] == "정보처리기사"
        assert metadata["categories"] == "국가기술자격"
        assert metadata["series"] == "정보처리"
        assert metadata["difficulty"] == 3
        assert metadata["study_period_days"] == 90
        assert "IT, 소프트웨어" in metadata["industry"]
        assert metadata["exam_type"] == "필기+실기"


class TestFormatterIntegration:
    """EmbeddingService와 VectorStoreService 통합 테스트."""

    def test_embedding_service_uses_common_formatter(self):
        """EmbeddingService가 공통 포맷터를 사용하는지 테스트."""
        from app.services.embedding_service import EmbeddingService
        from app.utils.certificate_formatter import format_certificate_text

        service = EmbeddingService()

        cert = {
            "title": "테스트 자격증",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "overview": "테스트 개요",
        }

        # 두 방법의 결과가 동일해야 함
        direct_result = format_certificate_text(cert)
        service_result = service.format_certificate_for_embedding(cert)

        assert direct_result == service_result

    def test_vector_store_uses_common_formatter(self):
        """VectorStoreService가 공통 포맷터(format_contextual_search_text)를 사용하는지 테스트."""
        from unittest.mock import MagicMock, patch

        from app.utils.certificate_formatter import format_contextual_search_text

        with patch("app.services.embedding.vector_store.get_settings") as mock_settings:
            mock_settings.return_value.CHROMA_HOST = "test-host"
            mock_settings.return_value.CHROMA_PORT = 8000
            mock_settings.return_value.CHROMA_COLLECTION_NAME = "test-collection"

            with patch("app.services.embedding.vector_store.chromadb") as mock_chromadb:
                mock_client = MagicMock()
                mock_chromadb.HttpClient.return_value = mock_client
                mock_collection = MagicMock()
                mock_client.get_or_create_collection.return_value = mock_collection
                mock_client.heartbeat.return_value = 1234567890

                from app.services.vector_store import VectorStoreService

                service = VectorStoreService()

                cert = {
                    "id": "cert-123",
                    "title": "테스트 자격증",
                    "categories": [{"code": "T", "name": "국가기술자격"}],
                    "series": "정보처리",
                    "overview": "테스트 개요",
                    "difficulty": 3,
                    "study_period_days": 90,
                    "career_info": {},
                    "exam_info": {},
                    "user_reviews": {},
                    "study_guide": {},
                }

                record = service.format_record_for_upsert(cert)
                direct_text = format_contextual_search_text(cert)

                # chunk_text가 Contextual 포맷터 결과와 동일해야 함
                assert record["chunk_text"] == direct_text


class TestBuildMetadataDomain:
    """build_certificate_metadata의 domain 메타데이터 테스트."""

    def test_build_metadata_includes_domain(self):
        """build_certificate_metadata가 domain 필드를 포함한다."""
        from app.utils.certificate_formatter import build_certificate_metadata

        cert = {
            "title": "정보처리기사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "기사",
            "domain": "IT/소프트웨어",
        }
        metadata = build_certificate_metadata(cert)
        assert metadata["domain"] == "IT/소프트웨어"

    def test_build_metadata_domain_defaults_empty(self):
        """domain이 없으면 빈 문자열로 기본값 설정."""
        from app.utils.certificate_formatter import build_certificate_metadata

        cert = {
            "title": "테스트",
            "categories": [],
        }
        metadata = build_certificate_metadata(cert)
        assert metadata["domain"] == ""
