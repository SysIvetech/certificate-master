"""QueryGenerator 테스트.

이 모듈은 자격증 유형별 최적화된 검색 쿼리 생성을 테스트합니다.
"""


class TestQueryGeneratorBasic:
    """QueryGenerator 기본 기능 테스트."""

    def test_query_generator_can_be_imported(self):
        """QueryGenerator를 임포트할 수 있어야 합니다."""
        from app.services.search.query_generator import QueryGenerator

        assert QueryGenerator is not None

    def test_query_generator_initialization(self):
        """QueryGenerator가 올바르게 초기화되어야 합니다."""
        from app.services.search.query_generator import QueryGenerator

        generator = QueryGenerator(
            certificate_title="정보처리기사",
            certificate_type="국가기술",
        )

        assert generator.title == "정보처리기사"
        assert generator.type == "국가기술"

    def test_query_generator_with_title_only(self):
        """자격증명만으로 초기화할 수 있어야 합니다."""
        from app.services.search.query_generator import QueryGenerator

        generator = QueryGenerator(certificate_title="정보처리기사")

        assert generator.title == "정보처리기사"
        assert generator.type is None


class TestQueryConfig:
    """QueryConfig 데이터클래스 테스트."""

    def test_query_config_can_be_imported(self):
        """QueryConfig를 임포트할 수 있어야 합니다."""
        from app.services.search.query_generator import QueryConfig

        assert QueryConfig is not None

    def test_query_config_creation(self):
        """QueryConfig가 올바르게 생성되어야 합니다."""
        from app.services.search.query_generator import QueryConfig

        config = QueryConfig(
            query="정보처리기사 시험일정",
            keywords=["시험", "일정"],
            priority="high",
            required=True,
        )

        assert config.query == "정보처리기사 시험일정"
        assert config.keywords == ["시험", "일정"]
        assert config.priority == "high"
        assert config.required is True

    def test_query_config_default_values(self):
        """QueryConfig의 기본값이 올바르게 설정되어야 합니다."""
        from app.services.search.query_generator import QueryConfig

        config = QueryConfig(query="정보처리기사")

        assert config.keywords == []
        assert config.priority == "normal"
        assert config.required is False


class TestBuildQueries:
    """build_queries 메서드 테스트."""

    def test_build_queries_returns_dict(self):
        """build_queries가 딕셔너리를 반환해야 합니다."""
        from app.services.search.query_generator import QueryGenerator

        generator = QueryGenerator(certificate_title="정보처리기사")
        queries = generator.build_queries()

        assert isinstance(queries, dict)

    def test_build_queries_contains_official_category(self):
        """build_queries에 'official' 카테고리가 포함되어야 합니다."""
        from app.services.search.query_generator import QueryGenerator

        generator = QueryGenerator(certificate_title="정보처리기사")
        queries = generator.build_queries()

        assert "official" in queries

    def test_official_query_uses_site_operator(self):
        """official 쿼리는 site: 연산자를 사용해야 합니다."""
        from app.services.search.query_generator import QueryGenerator

        generator = QueryGenerator(certificate_title="정보처리기사")
        queries = generator.build_queries()

        official_query = queries["official"]
        assert (
            "site:q-net.or.kr" in official_query.query
            or "site:hrdkorea.or.kr" in official_query.query
        )

    def test_official_query_is_required(self):
        """official 쿼리는 required=True여야 합니다."""
        from app.services.search.query_generator import QueryGenerator

        generator = QueryGenerator(certificate_title="정보처리기사")
        queries = generator.build_queries()

        official_query = queries["official"]
        assert official_query.required is True

    def test_official_query_has_high_priority(self):
        """official 쿼리는 priority='high'여야 합니다."""
        from app.services.search.query_generator import QueryGenerator

        generator = QueryGenerator(certificate_title="정보처리기사")
        queries = generator.build_queries()

        official_query = queries["official"]
        assert official_query.priority == "high"

    def test_build_queries_contains_standard_categories(self):
        """build_queries에 표준 카테고리들이 포함되어야 합니다."""
        from app.services.search.query_generator import QueryGenerator

        generator = QueryGenerator(certificate_title="정보처리기사")
        queries = generator.build_queries()

        # 계획에 명시된 카테고리들
        expected_categories = [
            "general",
            "statistics",
            "career",
            "reviews",
            "study_methods",
        ]

        for category in expected_categories:
            assert category in queries, f"'{category}' category should exist"


class TestCertificateTypeOptimization:
    """자격증 유형별 쿼리 최적화 테스트."""

    def test_national_technical_certificate_queries(self):
        """국가기술자격증 쿼리가 최적화되어야 합니다."""
        from app.services.search.query_generator import QueryGenerator

        generator = QueryGenerator(
            certificate_title="정보처리기사",
            certificate_type="국가기술",
        )
        queries = generator.build_queries()

        # 국가기술자격은 Q-Net 중심
        official_query = queries["official"]
        assert "q-net.or.kr" in official_query.query

    def test_national_professional_certificate_queries(self):
        """국가전문자격증 쿼리가 최적화되어야 합니다."""
        from app.services.search.query_generator import QueryGenerator

        generator = QueryGenerator(
            certificate_title="공인중개사",
            certificate_type="국가전문",
        )
        queries = generator.build_queries()

        # 국가전문자격도 공식 출처 포함
        assert "official" in queries

    def test_private_certificate_queries(self):
        """민간자격증 쿼리가 적절히 생성되어야 합니다."""
        from app.services.search.query_generator import QueryGenerator

        generator = QueryGenerator(
            certificate_title="컴퓨터활용능력",
            certificate_type="민간",
        )
        queries = generator.build_queries()

        # 민간자격도 기본 카테고리 포함
        assert "general" in queries
        assert "reviews" in queries


class TestOfficialDomains:
    """공식 도메인 관련 테스트."""

    def test_official_domains_constant_exists(self):
        """OFFICIAL_DOMAINS 상수가 존재해야 합니다."""
        from app.services.search.query_generator import OFFICIAL_DOMAINS

        assert isinstance(OFFICIAL_DOMAINS, set)

    def test_official_domains_contains_qnet(self):
        """OFFICIAL_DOMAINS에 q-net.or.kr이 포함되어야 합니다."""
        from app.services.search.query_generator import OFFICIAL_DOMAINS

        assert "q-net.or.kr" in OFFICIAL_DOMAINS

    def test_official_domains_contains_hrdkorea(self):
        """OFFICIAL_DOMAINS에 hrdkorea.or.kr이 포함되어야 합니다."""
        from app.services.search.query_generator import OFFICIAL_DOMAINS

        assert "hrdkorea.or.kr" in OFFICIAL_DOMAINS

    def test_is_official_domain_function_exists(self):
        """is_official_domain 함수가 존재해야 합니다."""
        from app.services.search.query_generator import is_official_domain

        assert callable(is_official_domain)

    def test_is_official_domain_detects_qnet(self):
        """is_official_domain이 Q-Net URL을 감지해야 합니다."""
        from app.services.search.query_generator import is_official_domain

        assert is_official_domain("https://www.q-net.or.kr/crf005.do") is True
        assert is_official_domain("https://q-net.or.kr/man001.do") is True

    def test_is_official_domain_rejects_non_official(self):
        """is_official_domain이 비공식 URL을 거부해야 합니다."""
        from app.services.search.query_generator import is_official_domain

        assert is_official_domain("https://blog.naver.com/abc") is False
        assert is_official_domain("https://tistory.com/123") is False
