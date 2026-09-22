"""EmbeddingService 텍스트 포맷팅 및 OpenAI 임베딩 생성 테스트.

OpenAI API를 사용하여 텍스트를 벡터로 변환합니다.
"""

from unittest.mock import MagicMock, patch


class TestEmbeddingService:
    """EmbeddingService 텍스트 포맷팅 테스트."""

    def test_init_with_api_key(self):
        """API 키로 초기화 테스트 (하위 호환성)."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService(api_key="test-api-key")
        assert service.api_key == "test-api-key"

    def test_init_without_api_key(self):
        """API 키 없이 초기화 테스트."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()
        assert service.api_key is None

    def test_format_certificate_for_embedding_basic(self):
        """기본 필드로 포맷팅 테스트."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        cert = {
            "title": "정보처리기사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "정보처리",
            "overview": "IT 분야의 대표적인 국가자격증입니다.",
            "difficulty": 3,
            "study_period_days": 90,
        }

        result = service.format_certificate_for_embedding(cert)

        assert "자격증: 정보처리기사" in result
        assert "분류: 국가기술자격" in result
        assert "계열: 정보처리" in result
        assert "개요: IT 분야의 대표적인 국가자격증입니다." in result
        assert "난이도: 3/5" in result
        assert "준비기간: 90일" in result

    def test_format_certificate_with_career_info(self):
        """진로 정보 포맷팅 테스트."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        cert = {
            "title": "정보처리기사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "overview": "IT 자격증",
            "career_info": {
                "use_cases": ["소프트웨어 개발", "시스템 분석"],
                "related_jobs": ["개발자", "PM", "SE"],
            },
        }

        result = service.format_certificate_for_embedding(cert)

        assert "활용분야: 소프트웨어 개발, 시스템 분석" in result
        assert "관련직업: 개발자, PM, SE" in result

    def test_format_certificate_with_exam_info(self):
        """시험 정보 포맷팅 테스트."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        cert = {
            "title": "정보처리기사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "overview": "IT 자격증",
            "exam_info": {
                "subjects": ["소프트웨어 설계", "데이터베이스", "운영체제"],
            },
        }

        result = service.format_certificate_for_embedding(cert)

        assert "시험과목: 소프트웨어 설계, 데이터베이스, 운영체제" in result

    def test_format_certificate_with_empty_fields(self):
        """빈 필드 처리 테스트."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        cert = {
            "title": "테스트 자격증",
            "categories": [{"code": "T", "name": "테스트"}],
        }

        result = service.format_certificate_for_embedding(cert)

        assert "자격증: 테스트 자격증" in result
        assert "분류: 테스트" in result


class TestFormatCertificateForEmbeddingEnhanced:
    """확장된 임베딩 텍스트 포맷 테스트."""

    def test_format_with_extended_career_info(self):
        """확장 진로 정보 포맷팅 테스트."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        cert = {
            "title": "관세사",
            "categories": [{"code": "S", "name": "국가전문자격"}],
            "series": "관세사",
            "overview": "관세사는 무역 관련 전문 자격증입니다.",
            "difficulty": 5,
            "study_period_days": 1095,
            "career_info": {
                "use_cases": ["수출입 통관", "관세법 컨설팅"],
                "related_jobs": ["관세사", "무역 전문가"],
                "industry": ["무역", "물류"],
                "job_prospects": "관세사는 무역 분야에서 필수적인 역할을 합니다.",
                "average_salary": "연 4,000만원 ~ 5,000만원",
            },
        }

        result = service.format_certificate_for_embedding(cert)

        # 기존 필드
        assert "활용분야: 수출입 통관, 관세법 컨설팅" in result
        assert "관련직업: 관세사, 무역 전문가" in result
        # 확장 필드
        assert "산업분야: 무역, 물류" in result
        assert "취업전망: 관세사는 무역 분야에서 필수적인 역할을 합니다." in result
        assert "평균연봉: 연 4,000만원 ~ 5,000만원" in result

    def test_format_with_extended_exam_info(self):
        """확장 시험 정보 포맷팅 테스트."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        cert = {
            "title": "관세사",
            "categories": [{"code": "S", "name": "국가전문자격"}],
            "overview": "관세사 시험",
            "exam_info": {
                "subjects": ["관세법개론", "무역영어", "내국소비세법"],
                "exam_type": "필기+실기 (OMR)",
                "exam_structure": "1차 필기 160문항 8시간, 2차 실무 4과목",
                "passing_criteria": "매 과목 40점 이상, 평균 60점 이상",
                "pass_rate_trend": "2023년 10%, 2024년 12%, 2025년 15%",
                "recent_trends": "최근 3년간 관세법 개정 사항 문제가 자주 출제",
            },
        }

        result = service.format_certificate_for_embedding(cert)

        # 기존 필드
        assert "시험과목: 관세법개론, 무역영어, 내국소비세법" in result
        # 확장 필드
        assert "시험유형: 필기+실기 (OMR)" in result
        assert "시험구성: 1차 필기 160문항 8시간, 2차 실무 4과목" in result
        assert "합격기준: 매 과목 40점 이상, 평균 60점 이상" in result
        assert "합격률추이: 2023년 10%, 2024년 12%, 2025년 15%" in result
        assert "최근출제동향: 최근 3년간 관세법 개정 사항 문제가 자주 출제" in result

    def test_format_with_user_reviews(self):
        """학습자 후기 포맷팅 테스트."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        cert = {
            "title": "관세사",
            "categories": [{"code": "S", "name": "국가전문자격"}],
            "overview": "관세사 시험",
            "user_reviews": {
                "summary": "관세사 시험은 매우 높은 난이도로 알려져 있습니다.",
                "difficulty_feedback": "시험의 난이도는 매우 높습니다.",
                "study_tips": [
                    "기출문제를 반복적으로 풀어보세요.",
                    "관세법과 무역실무 기본 개념을 철저히 이해하세요.",
                    "매일 일정 시간 학습하세요.",
                ],
            },
        }

        result = service.format_certificate_for_embedding(cert)

        assert "후기요약: 관세사 시험은 매우 높은 난이도로 알려져 있습니다." in result
        assert "난이도피드백: 시험의 난이도는 매우 높습니다." in result
        # 상위 2개 학습팁
        assert "기출문제를 반복적으로 풀어보세요." in result
        assert "관세법과 무역실무 기본 개념을 철저히 이해하세요." in result

    def test_format_with_study_guide(self):
        """학습 가이드 포맷팅 테스트."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        cert = {
            "title": "관세사",
            "categories": [{"code": "S", "name": "국가전문자격"}],
            "overview": "관세사 시험",
            "study_guide": {
                "study_methods": [
                    "기본서를 1회독한 후 기출문제를 반복적으로 풀어봅니다.",
                    "강의를 통해 이해가 어려운 부분을 보완합니다.",
                    "스터디 그룹을 활용하세요.",
                ],
                "success_tips": [
                    "기출문제 3회 이상 반복 - 정답률 90% 목표",
                    "오답노트 작성 및 복습",
                    "매일 일정 시간 학습 습관 유지",
                ],
            },
        }

        result = service.format_certificate_for_embedding(cert)

        # 상위 2개 학습 방법
        assert "기본서를 1회독한 후 기출문제를 반복적으로 풀어봅니다." in result
        assert "강의를 통해 이해가 어려운 부분을 보완합니다." in result
        # 상위 3개 성공 팁
        assert "기출문제 3회 이상 반복 - 정답률 90% 목표" in result
        assert "오답노트 작성 및 복습" in result
        assert "매일 일정 시간 학습 습관 유지" in result

    def test_format_complete_certificate(self):
        """모든 필드 포맷팅 테스트."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        cert = {
            "title": "정보처리기사",
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "정보처리",
            "overview": "IT 분야의 대표적인 국가자격증입니다.",
            "difficulty": 3,
            "study_period_days": 90,
            "career_info": {
                "use_cases": ["소프트웨어 개발"],
                "related_jobs": ["개발자", "PM"],
                "industry": ["IT", "소프트웨어"],
                "job_prospects": "IT 분야에서 필수 자격증입니다.",
                "average_salary": "연 3,500만원 ~ 6,000만원",
            },
            "exam_info": {
                "subjects": ["소프트웨어 설계", "데이터베이스"],
                "exam_type": "필기+실기",
                "exam_structure": "필기 100문항, 실기 논술+실무",
                "passing_criteria": "60점 이상",
                "pass_rate_trend": "필기 50%, 실기 40%",
                "recent_trends": "최신 IT 트렌드 문제 출제 증가",
            },
            "user_reviews": {
                "summary": "적당한 난이도로 IT 입문자에게 추천",
                "difficulty_feedback": "보통 난이도",
                "study_tips": ["기출문제 반복", "실기 코딩 연습"],
            },
            "study_guide": {
                "study_methods": ["필기 이론 정리", "실기 실습"],
                "success_tips": ["매일 2시간 학습", "기출문제 3회독"],
            },
        }

        result = service.format_certificate_for_embedding(cert)

        # 기본 정보
        assert "자격증: 정보처리기사" in result
        assert "난이도: 3/5" in result

        # 섹션 헤더 확인
        assert "[진로 정보]" in result
        assert "[시험 정보]" in result
        assert "[학습자 후기]" in result
        assert "[학습 가이드]" in result

        # 확장 필드 확인
        assert "산업분야:" in result
        assert "시험유형:" in result
        assert "후기요약:" in result
        assert "학습방법:" in result

    def test_format_with_missing_extended_fields(self):
        """확장 필드 누락 시 처리 테스트."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()

        cert = {
            "title": "테스트 자격증",
            "category": "테스트",
            "overview": "테스트 자격증입니다.",
            "career_info": {
                "use_cases": ["활용1"],
            },
            "exam_info": {
                "subjects": ["과목1"],
            },
        }

        result = service.format_certificate_for_embedding(cert)

        # 기존 필드는 포함
        assert "활용분야: 활용1" in result
        assert "시험과목: 과목1" in result
        # 누락 필드 섹션은 포함되지 않음
        assert "[학습자 후기]" not in result
        assert "[학습 가이드]" not in result


class TestOpenAIEmbedding:
    """OpenAI 임베딩 생성 테스트."""

    def setup_method(self):
        """각 테스트 전에 싱글톤 리셋."""
        from app.services.embedding_service import EmbeddingService

        EmbeddingService._client = None

    def test_client_singleton_initialization(self):
        """클라이언트가 싱글톤으로 초기화되는지 테스트."""
        with patch("app.services.embedding_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            from app.services.embedding_service import EmbeddingService

            service = EmbeddingService()

            # 첫 임베딩 호출 시 클라이언트 생성
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1024)]
            mock_client.embeddings.create.return_value = mock_response

            service.create_embedding("테스트")

            # 클라이언트가 한 번만 생성되어야 함 (싱글톤)
            assert mock_openai.call_count <= 1

    def test_create_embedding_returns_list(self):
        """단일 텍스트 임베딩이 리스트를 반환하는지 테스트."""
        with patch("app.services.embedding_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # OpenAI 응답 모킹
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1024)]
            mock_client.embeddings.create.return_value = mock_response

            from app.services.embedding_service import EmbeddingService

            service = EmbeddingService()
            result = service.create_embedding("정보처리기사")

            assert isinstance(result, list)
            assert len(result) == 1024  # OpenAI text-embedding-3-small 기본 차원

    def test_create_embedding_calls_api(self):
        """임베딩 생성 시 OpenAI API가 호출되는지 테스트."""
        with patch("app.services.embedding_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1024)]
            mock_client.embeddings.create.return_value = mock_response

            from app.services.embedding_service import EmbeddingService

            service = EmbeddingService()
            service.create_embedding("테스트 텍스트")

            mock_client.embeddings.create.assert_called_once()

    def test_create_embeddings_batch_returns_list_of_lists(self):
        """배치 임베딩이 2D 리스트를 반환하는지 테스트."""
        with patch("app.services.embedding_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # 3개 텍스트에 대한 임베딩
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.1] * 1024, index=0),
                MagicMock(embedding=[0.2] * 1024, index=1),
                MagicMock(embedding=[0.3] * 1024, index=2),
            ]
            mock_client.embeddings.create.return_value = mock_response

            from app.services.embedding_service import EmbeddingService

            service = EmbeddingService()
            texts = ["자격증1", "자격증2", "자격증3"]
            results = service.create_embeddings_batch(texts)

            assert isinstance(results, list)
            assert len(results) == 3
            for embedding in results:
                assert isinstance(embedding, list)
                assert len(embedding) == 1024

    def test_create_embedding_with_empty_text(self):
        """빈 텍스트에 대한 처리 테스트."""
        with patch("app.services.embedding_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.0] * 1024)]
            mock_client.embeddings.create.return_value = mock_response

            from app.services.embedding_service import EmbeddingService

            service = EmbeddingService()
            result = service.create_embedding("")

            assert isinstance(result, list)
            assert len(result) == 1024

    def test_create_embeddings_batch_empty_list(self):
        """빈 리스트에 대한 처리 테스트."""
        from app.services.embedding_service import EmbeddingService

        service = EmbeddingService()
        results = service.create_embeddings_batch([])

        assert results == []

    def test_create_embeddings_batch_preserves_order(self):
        """배치 임베딩 순서가 보존되는지 테스트."""
        with patch("app.services.embedding_service.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # 순서가 뒤섞인 응답 (index로 정렬 필요)
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.3] * 1024, index=2),
                MagicMock(embedding=[0.1] * 1024, index=0),
                MagicMock(embedding=[0.2] * 1024, index=1),
            ]
            mock_client.embeddings.create.return_value = mock_response

            from app.services.embedding_service import EmbeddingService

            service = EmbeddingService()
            results = service.create_embeddings_batch(["a", "b", "c"])

            # 순서가 index 기준으로 정렬되어야 함
            assert results[0][0] == 0.1  # index 0
            assert results[1][0] == 0.2  # index 1
            assert results[2][0] == 0.3  # index 2
