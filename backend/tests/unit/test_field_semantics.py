"""필드 의미론 테스트.

비슷한 이름의 필드들이 서로 다른 역할을 가지고 있음을 문서화하고 검증합니다.
"""


class TestIndustryFieldSemantics:
    """industry/preferred_industries 필드 의미론 테스트.

    이 테스트들은 비슷한 이름의 필드들이 서로 다른 맥락에서
    사용됨을 명확히 문서화합니다.
    """

    def test_career_info_industry_is_certificate_attribute(self):
        """career_info.industry는 '자격증이 관련된 산업'을 의미합니다.

        예시:
        - 정보처리기사: ["IT", "소프트웨어", "금융IT"]
        - 전기기사: ["전기공사", "제조업", "건설"]
        - 세무사: ["세무법인", "회계법인", "기업 재무팀"]

        이 필드는 자격증 자체의 속성으로, 이 자격증을 취득하면
        어떤 산업에서 활용할 수 있는지를 나타냅니다.
        """
        from app.services.llm.service import ExtractedCareerInfo

        career_info = ExtractedCareerInfo(
            industry=["IT", "소프트웨어", "금융IT"],
            use_cases=["시스템 개발", "데이터 분석"],
            related_jobs=["개발자", "데이터 분석가"],
        )

        # industry는 자격증이 활용되는 산업 분야
        assert "IT" in career_info.industry
        assert isinstance(career_info.industry, list)

    def test_job_market_preferred_industries_is_market_perspective(self):
        """job_market_info.preferred_industries는 '이 자격증을 선호하는 기업군'을 의미합니다.

        예시:
        - 세무사: ["세무법인", "회계법인", "금융업", "대기업 재무팀", "공기업"]
        - 정보처리기사: ["IT기업", "금융권", "공공기관"]

        이 필드는 채용 시장 관점에서, 실제로 이 자격증을 우대하거나
        필수로 요구하는 기업 유형을 나타냅니다.
        """
        from app.services.llm.service import ExtractedJobMarketInfo

        job_market = ExtractedJobMarketInfo(
            job_posting_frequency="월 50-100건",
            preferred_industries=["세무법인", "회계법인", "금융업"],
            requirement_type="우대",
            public_sector_points="5점",
        )

        # preferred_industries는 채용 시장에서 선호하는 기업군
        assert "세무법인" in job_market.preferred_industries
        assert isinstance(job_market.preferred_industries, list)

    def test_user_context_preferred_industries_is_user_preference(self):
        """StructuredUserContext.preferred_industries는 '사용자가 선호하는 산업'을 의미합니다.

        예시:
        - IT 취업 희망자: ["IT", "스타트업", "게임"]
        - 금융권 희망자: ["은행", "증권", "보험"]

        이 필드는 사용자 관점에서, 본인이 취업하고 싶은
        산업 분야를 나타냅니다.
        """
        from app.schemas.recommendation import StructuredUserContext

        user_context = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="전공자",
            weekly_study_hours=20,
            max_study_period_days=180,
            difficulty_preference="중",
            preferred_industries=["IT", "스타트업", "게임"],
        )

        # preferred_industries는 사용자가 가고 싶은 산업
        assert "IT" in user_context.preferred_industries
        assert isinstance(user_context.preferred_industries, list)

    def test_industry_fields_have_different_purposes(self):
        """세 필드가 서로 다른 목적으로 사용됨을 검증합니다.

        - career_info.industry: 자격증 → 산업 (자격증 속성)
        - job_market_info.preferred_industries: 시장 → 자격증 (채용 관점)
        - user_context.preferred_industries: 사용자 → 산업 (개인 선호)
        """
        from app.schemas.recommendation import StructuredUserContext
        from app.services.llm.service import ExtractedCareerInfo, ExtractedJobMarketInfo

        # 동일한 자격증(세무사)에 대해 각 필드의 의미 차이
        certificate_career_info = ExtractedCareerInfo(
            industry=["세무", "회계", "금융"],  # 자격증이 관련된 산업
            use_cases=["세무 신고", "회계 감사"],
            related_jobs=["세무사", "회계사"],
        )

        certificate_job_market = ExtractedJobMarketInfo(
            job_posting_frequency="높음",
            preferred_industries=[
                "세무법인",
                "회계법인",
                "대기업 재무팀",
            ],  # 채용하는 기업군
            requirement_type="필수",
        )

        user_preference = StructuredUserContext(
            goal="취업",
            employment_status="학생",
            major_background="전공자",
            weekly_study_hours=20,
            max_study_period_days=180,
            difficulty_preference="중",
            preferred_industries=["대기업", "공기업"],  # 사용자가 가고 싶은 곳
        )

        # 각 필드의 역할이 명확히 구분됨
        assert (
            certificate_career_info.industry
            != certificate_job_market.preferred_industries
        )
        assert (
            certificate_job_market.preferred_industries
            != user_preference.preferred_industries
        )


class TestFieldNamingConsistency:
    """필드 네이밍 일관성 테스트."""

    def test_industry_vs_preferred_industries_naming(self):
        """industry(단수)와 preferred_industries(복수)의 네이밍 규칙을 문서화합니다.

        - industry: 자격증이 속한 산업 분야 (일반적 분류)
        - preferred_industries: 특정 기업군 (구체적 기업 유형)

        네이밍 규칙:
        - 일반 분류 → 단수형 (industry)
        - 구체적 기업군 → 복수형 (preferred_industries)
        """
        from app.services.llm.service import ExtractedCareerInfo, ExtractedJobMarketInfo

        # career_info.industry - 일반적 산업 분류
        career = ExtractedCareerInfo(
            industry=["IT", "금융", "제조"],  # 산업 '분야'
        )

        # job_market_info.preferred_industries - 구체적 기업군
        market = ExtractedJobMarketInfo(
            preferred_industries=["IT대기업", "금융권", "공기업"],  # 기업 '유형'
        )

        # 두 필드 모두 list[str] 타입
        assert isinstance(career.industry, list)
        assert isinstance(market.preferred_industries, list)
