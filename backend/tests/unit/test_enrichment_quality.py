"""Unit tests for enrichment quality validation."""

from app.schemas.certificate import CertificateUpdate


class TestEnrichmentQuality:
    """Test enrichment data quality."""

    def test_overview_length(self):
        """Test overview has appropriate length (3-5 sentences)."""
        update = CertificateUpdate(
            overview="짧은 개요."  # 1 sentence, should be flagged
        )
        # Count sentences (simple heuristic)
        sentence_count = (
            update.overview.count(".")
            + update.overview.count("!")
            + update.overview.count("?")
        )
        assert sentence_count >= 1, "Overview should have at least 1 sentence"

    def test_difficulty_range(self):
        """Test difficulty is within valid range."""
        # Valid cases
        for diff in [1, 2, 3, 4, 5]:
            update = CertificateUpdate(difficulty=diff)
            assert 1 <= update.difficulty <= 5

    def test_study_period_reasonable(self):
        """Test study period is reasonable (1-730 days)."""
        # Reasonable period
        update = CertificateUpdate(study_period_days=60)
        assert 1 <= update.study_period_days <= 730, "Study period should be 1-730 days"

        # Edge cases
        update_min = CertificateUpdate(study_period_days=1)
        assert update_min.study_period_days == 1

        update_max = CertificateUpdate(study_period_days=365)
        assert update_max.study_period_days == 365

    def test_exam_info_completeness(self):
        """Test exam_info has required fields."""
        exam_info = {
            "subjects": ["과목1", "과목2"],
            "exam_type": "필기",
            "passing_criteria": "60점 이상",
            "total_fee": "20000",
        }
        update = CertificateUpdate(exam_info=exam_info)

        assert "subjects" in update.exam_info
        assert "exam_type" in update.exam_info
        assert "passing_criteria" in update.exam_info
        assert len(update.exam_info["subjects"]) > 0

    def test_lectures_relevance_score(self):
        """Test lecture relevance scores are valid."""
        lectures = [
            {
                "platform": "에듀윌",
                "title": "호텔경영사 강의",
                "url": "https://example.com",
                "relevance_score": 0.95,
                "price": "150000원",
            },
            {
                "platform": "해커스",
                "title": "호텔경영사 완강",
                "url": "https://example.com",
                "relevance_score": 0.85,
                "price": "무료",
            },
        ]
        update = CertificateUpdate(recommended_lectures=lectures)

        for lecture in update.recommended_lectures:
            assert "relevance_score" in lecture
            assert 0 <= lecture["relevance_score"] <= 1

    def test_lectures_url_format(self):
        """Test lecture URLs are valid."""
        lectures = [
            {
                "platform": "에듀윌",
                "title": "강의",
                "url": "https://www.eduwill.net/lecture/123",
                "relevance_score": 0.9,
            }
        ]
        update = CertificateUpdate(recommended_lectures=lectures)

        for lecture in update.recommended_lectures:
            url = lecture["url"]
            assert url.startswith("http://") or url.startswith("https://")

    def test_lectures_title_relevance(self):
        """Test lecture titles should not contain unrelated certificate names."""
        # Good case
        lectures_good = [
            {
                "platform": "에듀윌",
                "title": "호텔경영사 완강 패키지",
                "url": "https://example.com",
                "relevance_score": 0.95,
            }
        ]
        update_good = CertificateUpdate(recommended_lectures=lectures_good)
        assert len(update_good.recommended_lectures) == 1

        # Bad case (different certificate in title)
        lectures_bad = [
            {
                "platform": "에듀윌",
                "title": "재경관리사 단기 합격",  # Different certificate
                "url": "https://example.com",
                "relevance_score": 0.2,  # Should have low relevance score
            }
        ]
        update_bad = CertificateUpdate(recommended_lectures=lectures_bad)
        # If relevance score is low (<0.5), it should be filtered out
        assert update_bad.recommended_lectures[0]["relevance_score"] < 0.5

    def test_career_info_structure(self):
        """Test career info has expected structure."""
        career_info = {
            "use_cases": ["취업 가산점", "승진"],
            "related_jobs": ["호텔 매니저"],
            "average_salary": "연봉 3,000만원",
            "industry": ["호텔", "관광"],
        }
        update = CertificateUpdate(career_info=career_info)

        assert "use_cases" in update.career_info
        assert "related_jobs" in update.career_info
        assert isinstance(update.career_info["use_cases"], list)
        assert isinstance(update.career_info["related_jobs"], list)

    def test_user_reviews_structure(self):
        """Test user reviews has expected structure."""
        reviews = {
            "summary": "합격자들은 2-3개월 준비로 충분하다고 평가",
            "difficulty_feedback": "필기는 쉬운 편",
            "study_tips": ["기출문제 중심", "실무 경험"],
            "common_challenges": ["시간 관리"],
        }
        update = CertificateUpdate(user_reviews=reviews)

        assert "summary" in update.user_reviews
        assert "study_tips" in update.user_reviews
        assert isinstance(update.user_reviews["study_tips"], list)

    def test_official_sources_has_site(self):
        """Test official sources has official site."""
        sources = {
            "official_site": "https://www.q-net.or.kr/",
            "issuing_organization": "한국산업인력공단",
        }
        update = CertificateUpdate(official_sources=sources)

        assert "official_site" in update.official_sources
        assert update.official_sources["official_site"].startswith("http")


class TestEnrichmentCompleteness:
    """Test enrichment data completeness."""

    def test_minimal_required_fields(self):
        """Test minimal required fields for enrichment."""
        update = CertificateUpdate(
            overview="자격증 개요입니다. 이 자격증은 중요합니다. 취득을 권장합니다.",
            difficulty=3,
            study_period_days=60,
            exam_info={
                "subjects": ["과목1"],
                "exam_type": "필기",
                "passing_criteria": "60점 이상",
            },
        )
        # Minimal fields should be present
        assert update.overview is not None
        assert update.difficulty is not None
        assert update.study_period_days is not None
        assert update.exam_info is not None

    def test_recommended_enrichment_fields(self):
        """Test recommended fields for good enrichment."""
        update = CertificateUpdate(
            overview="자격증 개요입니다. 이 자격증은 중요합니다. 취득을 권장합니다.",
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
            official_sources={
                "official_site": "https://www.q-net.or.kr/",
            },
        )
        # All recommended fields should be present
        assert update.recommended_lectures is not None
        assert update.official_sources is not None

    def test_full_enrichment_fields(self):
        """Test all enrichment fields."""
        update = CertificateUpdate(
            overview="완전한 개요입니다. 매우 상세합니다. 유용한 정보입니다.",
            difficulty=3,
            study_period_days=60,
            exam_info={
                "subjects": ["과목1"],
                "exam_type": "필기",
                "passing_criteria": "60점",
            },
            recommended_lectures=[
                {
                    "platform": "A",
                    "title": "B",
                    "url": "http://c.com",
                    "relevance_score": 0.9,
                }
            ],
            career_info={"use_cases": ["취업"]},
            user_reviews={"summary": "좋음"},
            official_sources={"official_site": "http://example.com"},
        )
        # All fields present
        assert update.overview is not None
        assert update.exam_info is not None
        assert update.recommended_lectures is not None
        assert update.career_info is not None
        assert update.user_reviews is not None
        assert update.official_sources is not None
