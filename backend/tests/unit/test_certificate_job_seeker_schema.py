"""취업준비생 관점 Certificate 스키마 테스트.

TDD: 새로운 취업준비생 관점 필드 테스트.
"""


class TestJobMarketInfoSchema:
    """채용 시장 정보 스키마 테스트."""

    def test_job_market_info_valid(self):
        """유효한 채용 시장 정보 생성."""
        from app.schemas.certificate import JobMarketInfo

        info = JobMarketInfo(
            job_posting_frequency="매우 많음",
            preferred_industries=["IT", "금융", "제조"],
            requirement_type="우대",
            public_sector_points="필기 5%, 실기 3%",
        )

        assert info.job_posting_frequency == "매우 많음"
        assert len(info.preferred_industries) == 3
        assert "IT" in info.preferred_industries

    def test_job_market_info_optional_fields(self):
        """선택적 필드만 포함."""
        from app.schemas.certificate import JobMarketInfo

        info = JobMarketInfo()

        assert info.job_posting_frequency is None
        assert info.preferred_industries == []


class TestCostBreakdownSchema:
    """비용 상세 스키마 테스트."""

    def test_cost_breakdown_valid(self):
        """유효한 비용 정보 생성."""
        from app.schemas.certificate import CostBreakdown

        cost = CostBreakdown(
            exam_fee="필기 19,400원 + 실기 22,600원",
            exam_fee_refund="시험 3일 전까지 100% 환불",
            textbook_cost="30,000 ~ 50,000원",
            lecture_cost="100,000 ~ 300,000원",
            total_estimated_cost="150,000 ~ 400,000원",
            free_resources=["큐넷 기출문제", "유튜브 무료 강의"],
        )

        assert "19,400원" in cost.exam_fee
        assert len(cost.free_resources) == 2


class TestFeasibilityInfoSchema:
    """합격 가능성 스키마 테스트."""

    def test_feasibility_info_valid(self):
        """유효한 합격 가능성 정보 생성."""
        from app.schemas.certificate import FeasibilityInfo

        info = FeasibilityInfo(
            non_major_pass_rate="약 30-35%",
            working_adult_tips=["출퇴근 시간 활용", "CBT 상시 응시"],
            self_study_possible=True,
            minimum_study_period=30,
            first_attempt_pass_rate="약 40%",
        )

        assert info.self_study_possible is True
        assert info.minimum_study_period == 30


class TestExamScheduleDetailSchema:
    """시험 일정 상세 스키마 테스트."""

    def test_exam_schedule_detail_valid(self):
        """유효한 시험 일정 정보 생성."""
        from app.schemas.certificate import ExamScheduleDetail

        detail = ExamScheduleDetail(
            annual_exam_count=3,
            exam_type="필기(CBT) + 실기(정기)",
            next_exam_date="2026-03-15",
            registration_period="2026-02-01 ~ 2026-02-07",
            result_announcement="시험 후 2주 내",
        )

        assert detail.annual_exam_count == 3
        assert detail.exam_type == "필기(CBT) + 실기(정기)"


class TestSimilarCertificateSchema:
    """유사 자격증 비교 스키마 테스트."""

    def test_similar_certificate_valid(self):
        """유효한 유사 자격증 정보 생성."""
        from app.schemas.certificate import SimilarCertificate

        similar = SimilarCertificate(
            certificate_id="uuid-123",
            title="정보처리산업기사",
            comparison="기사보다 난이도 낮음, 실무 경력 대신 취득 가능",
        )

        assert similar.title == "정보처리산업기사"


class TestCertificateSchemaWithJobSeekerFields:
    """Certificate 스키마에 취업준비생 필드 포함 테스트."""

    def test_certificate_has_job_seeker_fields(self):
        """Certificate 스키마에 취업준비생 필드가 있어야 함."""
        from app.schemas.certificate import Certificate, CertificateUpdate

        # Certificate 필드 확인
        cert_fields = Certificate.model_fields
        assert "job_market_info" in cert_fields
        assert "cost_breakdown" in cert_fields
        assert "feasibility_info" in cert_fields
        assert "exam_schedule_detail" in cert_fields
        assert "similar_certificates" in cert_fields

        # CertificateUpdate 필드 확인
        update_fields = CertificateUpdate.model_fields
        assert "job_market_info" in update_fields
        assert "cost_breakdown" in update_fields
        assert "feasibility_info" in update_fields
        assert "exam_schedule_detail" in update_fields
        assert "similar_certificates" in update_fields


class TestViewCountField:
    """조회수 필드 테스트."""

    def test_certificate_has_view_count_field(self):
        """Certificate 스키마에 view_count 필드가 있어야 함."""
        from app.schemas.certificate import Certificate

        cert_fields = Certificate.model_fields
        assert "view_count" in cert_fields

    def test_view_count_default_is_zero(self):
        """view_count 기본값은 0이어야 함."""
        from app.schemas.certificate import Certificate

        # view_count 필드의 기본값 확인
        field_info = Certificate.model_fields["view_count"]
        assert field_info.default == 0
