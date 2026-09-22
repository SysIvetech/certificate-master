"""Unit tests for Certificate schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas.certificate import (
    CareerInfo,
    Certificate,
    CertificateUpdate,
    OfficialSources,
    RecommendedLecture,
    UserReviews,
)


class TestCareerInfo:
    """Test CareerInfo schema."""

    def test_career_info_valid(self):
        """Test valid career info."""
        career = CareerInfo(
            use_cases=["취업 가산점", "승진 필수"],
            related_jobs=["호텔 매니저", "관광 기획자"],
            average_salary="연봉 3,000만원 ~ 5,000만원",
            job_prospects="수요 증가 중",
            industry=["호텔", "관광"],
        )
        assert len(career.use_cases) == 2
        assert career.average_salary is not None
        assert len(career.industry) == 2


class TestUserReviews:
    """Test UserReviews schema."""

    def test_user_reviews_valid(self):
        """Test valid user reviews."""
        reviews = UserReviews(
            summary="합격자들은 2-3개월 준비로 충분하다고 평가",
            difficulty_feedback="필기는 쉬운 편이나 면접이 까다로움",
            study_tips=["기출문제 중심", "실무 경험 중요"],
            common_challenges=["시간 관리", "면접 준비"],
        )
        assert reviews.summary is not None
        assert len(reviews.study_tips) == 2


class TestOfficialSources:
    """Test OfficialSources schema."""

    def test_official_sources_valid(self):
        """Test valid official sources."""
        sources = OfficialSources(
            official_site="https://www.q-net.or.kr/",
            issuing_organization="한국산업인력공단",
            reference_urls=["https://example.com/ref1"],
        )
        assert sources.official_site is not None
        assert sources.issuing_organization == "한국산업인력공단"


class TestRecommendedLecture:
    """Test RecommendedLecture schema."""

    def test_lecture_valid(self):
        """Test valid lecture."""
        lecture = RecommendedLecture(
            platform="에듀윌",
            title="호텔경영사 완강 패키지",
            url="https://example.com/lecture",
            instructor="홍길동",
            price="150000원",
            rating=4.5,
            review_count=100,
            relevance_score=0.95,
        )
        assert lecture.platform == "에듀윌"
        assert lecture.relevance_score == 0.95
        assert lecture.price == "150000원"

    def test_lecture_relevance_score_default(self):
        """Test lecture with default relevance score."""
        lecture = RecommendedLecture(
            platform="해커스",
            title="강의명",
            url="https://example.com",
        )
        assert lecture.relevance_score == 1.0

    def test_lecture_invalid_rating(self):
        """Test lecture with invalid rating."""
        with pytest.raises(ValidationError):
            RecommendedLecture(
                platform="에듀윌",
                title="강의",
                url="https://example.com",
                rating=6.0,  # Invalid: > 5
            )

    def test_lecture_invalid_relevance_score(self):
        """Test lecture with invalid relevance score."""
        with pytest.raises(ValidationError):
            RecommendedLecture(
                platform="에듀윌",
                title="강의",
                url="https://example.com",
                relevance_score=1.5,  # Invalid: > 1
            )


class TestCertificateUpdate:
    """Test CertificateUpdate schema."""

    def test_certificate_update_all_fields(self):
        """Test certificate update with all fields."""
        update = CertificateUpdate(
            overview="자격증 개요입니다.",
            difficulty=3,
            study_period_days=60,
            exam_info={
                "subjects": ["과목1", "과목2"],
                "exam_type": "필기+실기",
                "passing_criteria": "60점 이상",
                "total_fee": "20000",
            },
            recommended_lectures=[
                {
                    "platform": "에듀윌",
                    "title": "강의명",
                    "url": "https://example.com",
                    "relevance_score": 0.9,
                }
            ],
            career_info={
                "use_cases": ["취업 가산점"],
                "related_jobs": ["매니저"],
            },
            user_reviews={
                "summary": "좋은 자격증",
                "study_tips": ["팁1", "팁2"],
            },
            official_sources={
                "official_site": "https://www.q-net.or.kr/",
                "issuing_organization": "한국산업인력공단",
            },
        )
        assert update.overview is not None
        assert update.difficulty == 3
        assert update.exam_info is not None

    def test_certificate_update_difficulty_validation(self):
        """Test difficulty validation."""
        with pytest.raises(ValidationError):
            CertificateUpdate(difficulty=0)  # Invalid: < 1

        with pytest.raises(ValidationError):
            CertificateUpdate(difficulty=6)  # Invalid: > 5

    def test_certificate_update_study_period_validation(self):
        """Test study period validation."""
        with pytest.raises(ValidationError):
            CertificateUpdate(study_period_days=0)  # Invalid: < 1

    def test_certificate_update_passing_rate_validation(self):
        """Test passing rate validation."""
        with pytest.raises(ValidationError):
            CertificateUpdate(passing_rate=-1)  # Invalid: < 0

        with pytest.raises(ValidationError):
            CertificateUpdate(passing_rate=101)  # Invalid: > 100

    def test_certificate_update_rejects_exam_schedule(self):
        """Ensure deprecated exam_schedule field is rejected."""
        with pytest.raises(ValidationError):
            CertificateUpdate(exam_schedule="2026-01-01")  # type: ignore[arg-type]


class TestCertificateSchema:
    """Test Certificate schema (for DB response)."""

    def test_certificate_minimal(self):
        """Test certificate with minimal fields."""
        from datetime import datetime, timezone

        cert = Certificate(
            id="test-uuid",
            raw_id="S_테스트자격증",
            categories=[{"code": "S", "name": "국가전문자격"}],
            series="테스트",
            title="테스트자격증",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert cert.id == "test-uuid"
        assert cert.exam_info == {}
        assert cert.recommended_lectures == []
        assert len(cert.categories) == 1
        assert cert.categories[0].code == "S"

    def test_certificate_with_enrichment(self):
        """Test certificate with enriched data."""
        from datetime import datetime, timezone

        cert = Certificate(
            id="test-uuid",
            raw_id="S_테스트",
            categories=[{"code": "S", "name": "국가전문자격"}],
            series="테스트",
            title="테스트자격증",
            overview="테스트 개요",
            difficulty=3,
            study_period_days=60,
            exam_info={
                "subjects": ["과목1"],
                "exam_type": "필기",
                "passing_criteria": "60점 이상",
                "total_fee": "20000",
            },
            recommended_lectures=[
                {
                    "platform": "에듀윌",
                    "title": "강의",
                    "url": "https://example.com",
                    "relevance_score": 0.9,
                }
            ],
            career_info={
                "use_cases": ["취업"],
            },
            user_reviews={
                "summary": "좋음",
            },
            official_sources={
                "official_site": "https://example.com",
            },
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert cert.overview == "테스트 개요"
        assert cert.difficulty == 3
        assert len(cert.recommended_lectures) == 1
        assert cert.career_info != {}

    def test_certificate_domain_field_present(self):
        """Certificate 스키마에 domain 필드가 존재해야 한다."""
        from datetime import datetime, timezone

        cert = Certificate(
            id="test-uuid",
            raw_id="T_정보처리기사",
            categories=[{"code": "T", "name": "국가기술자격"}],
            series="기사",
            title="정보처리기사",
            domain="IT/소프트웨어",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert cert.domain == "IT/소프트웨어"

    def test_certificate_domain_nullable(self):
        """domain 필드는 nullable이다."""
        from datetime import datetime, timezone

        cert = Certificate(
            id="test-uuid",
            raw_id="T_테스트",
            categories=[{"code": "T", "name": "국가기술자격"}],
            title="테스트자격증",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert cert.domain is None

    def test_certificate_domain_in_api_response(self):
        """domain 필드가 직렬화된 응답에 포함되어야 한다."""
        from datetime import datetime, timezone

        cert = Certificate(
            id="test-uuid",
            raw_id="T_전기기사",
            categories=[{"code": "T", "name": "국가기술자격"}],
            title="전기기사",
            domain="전기/전자",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        data = cert.model_dump()
        assert "domain" in data
        assert data["domain"] == "전기/전자"
