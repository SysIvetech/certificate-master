"""data_pipeline.py 개선사항에 대한 단위 테스트.

테스트 대상:
1. LLM 창의성 제거 (temperature 변경)
2. total_estimated_cost 필드 제거
3. 자격증 개요 독립 문장 스타일
4. 시험 정보 필드 추가 (acquisition_method, exam_criteria_url)
5. 준비기간 분포 제거 (study_period_distribution, study_period_range_days)
6. 직장인 학습 팁 제거 (working_adult_tips)
7. 연봉 프리미엄 제거 (salary_premium)
8. 취업 전망 상세화 (job_prospects 4-5문장)
9. 학습 순서 → 핵심 출제 토픽 (learning_sequence → key_exam_topics)
"""


class TestExtractedModelsFieldRemoval:
    """제거해야 할 필드들이 모델에서 제거되었는지 검증."""

    def test_extracted_cost_breakdown_no_total_estimated_cost(self):
        """#2: total_estimated_cost 필드가 제거되었는지 확인."""
        from app.services.llm.service import ExtractedCostBreakdown

        model = ExtractedCostBreakdown(
            exam_fee="필기 19,400원 + 실기 22,600원",
            textbook_cost="30,000 ~ 50,000원",
        )
        # total_estimated_cost 필드가 모델에 없어야 함
        assert not hasattr(model, "total_estimated_cost")
        assert "total_estimated_cost" not in model.model_fields

    def test_extracted_user_reviews_no_study_period_fields(self):
        """#5: study_period_distribution, study_period_range_days 필드가 제거되었는지 확인."""
        from app.services.llm.service import ExtractedUserReviews

        model = ExtractedUserReviews(summary="테스트 요약")
        # 해당 필드들이 모델에 없어야 함
        assert "study_period_distribution" not in model.model_fields
        assert "study_period_range_days" not in model.model_fields

    def test_extracted_feasibility_info_no_working_adult_tips(self):
        """#6: working_adult_tips 필드가 제거되었는지 확인."""
        from app.services.llm.service import ExtractedFeasibilityInfo

        model = ExtractedFeasibilityInfo(non_major_pass_rate="약 30%")
        # working_adult_tips 필드가 모델에 없어야 함
        assert "working_adult_tips" not in model.model_fields

    def test_extracted_job_market_info_no_salary_premium(self):
        """#7: salary_premium 필드가 제거되었는지 확인."""
        from app.services.llm.service import ExtractedJobMarketInfo

        model = ExtractedJobMarketInfo(job_posting_frequency="많음")
        # salary_premium 필드가 모델에 없어야 함
        assert "salary_premium" not in model.model_fields


class TestExtractedModelsNewFields:
    """추가해야 할 필드들이 모델에 존재하는지 검증."""

    def test_extracted_exam_info_has_acquisition_method(self):
        """#4: acquisition_method 필드가 추가되었는지 확인."""
        from app.services.llm.service import ExtractedExamInfo

        model = ExtractedExamInfo(
            subjects=["과목1", "과목2"],
            exam_type="필기+실기",
            passing_criteria="60점 이상",
            acquisition_method="응시자격: 관련학과 졸업 또는 경력 2년 이상",
        )
        assert model.acquisition_method == "응시자격: 관련학과 졸업 또는 경력 2년 이상"

    def test_extracted_exam_info_has_exam_criteria_url(self):
        """#4: exam_criteria_url 필드가 추가되었는지 확인."""
        from app.services.llm.service import ExtractedExamInfo

        model = ExtractedExamInfo(
            subjects=["과목1"],
            exam_type="필기",
            passing_criteria="60점 이상",
            exam_criteria_url="https://www.q-net.or.kr/criteria",
        )
        assert model.exam_criteria_url == "https://www.q-net.or.kr/criteria"

    def test_extracted_study_guide_has_key_exam_topics(self):
        """#9: key_exam_topics 필드가 추가되었는지 확인."""
        from app.services.llm.service import ExtractedStudyGuide

        model = ExtractedStudyGuide(
            study_methods=["기출문제 반복"],
            key_exam_topics=[
                {
                    "topic": "소프트웨어 설계",
                    "frequency": "매우 자주",
                    "importance": "상",
                    "description": "UML, 디자인 패턴",
                }
            ],
        )
        assert len(model.key_exam_topics) == 1
        assert model.key_exam_topics[0]["topic"] == "소프트웨어 설계"

    def test_extracted_study_guide_no_learning_sequence(self):
        """#9: learning_sequence 필드가 제거되었는지 확인."""
        from app.services.llm.service import ExtractedStudyGuide

        model = ExtractedStudyGuide(study_methods=["기출문제 반복"])
        # learning_sequence 필드가 모델에 없어야 함
        assert "learning_sequence" not in model.model_fields


class TestSchemaModelsFieldChanges:
    """API 응답 스키마(certificate.py)의 필드 변경 검증."""

    def test_cost_breakdown_schema_no_total_estimated_cost(self):
        """#2: CostBreakdown 스키마에서 total_estimated_cost 필드 제거 확인."""
        from app.schemas.certificate import CostBreakdown

        model = CostBreakdown(exam_fee="42,000원")
        assert "total_estimated_cost" not in model.model_fields

    def test_feasibility_info_schema_no_working_adult_tips(self):
        """#6: FeasibilityInfo 스키마에서 working_adult_tips 필드 제거 확인."""
        from app.schemas.certificate import FeasibilityInfo

        model = FeasibilityInfo(non_major_pass_rate="30%")
        assert "working_adult_tips" not in model.model_fields

    def test_job_market_info_schema_no_salary_premium(self):
        """#7: JobMarketInfo 스키마에서 salary_premium 필드 제거 확인."""
        from app.schemas.certificate import JobMarketInfo

        model = JobMarketInfo(job_posting_frequency="많음")
        assert "salary_premium" not in model.model_fields

    def test_study_guide_schema_has_key_exam_topics(self):
        """#9: StudyGuide 스키마에서 key_exam_topics 필드 추가 확인."""
        from app.schemas.certificate import StudyGuide

        model = StudyGuide(
            key_exam_topics=[
                {
                    "topic": "데이터베이스",
                    "frequency": "자주",
                    "importance": "상",
                }
            ]
        )
        assert len(model.key_exam_topics) == 1

    def test_study_guide_schema_no_learning_sequence(self):
        """#9: StudyGuide 스키마에서 learning_sequence 필드 제거 확인."""
        from app.schemas.certificate import StudyGuide

        model = StudyGuide()
        assert "learning_sequence" not in model.model_fields


class TestKeyExamTopicModel:
    """#9: ExtractedKeyExamTopic 모델 검증."""

    def test_key_exam_topic_model_exists(self):
        """ExtractedKeyExamTopic 모델이 존재하는지 확인."""
        from app.services.llm.service import ExtractedKeyExamTopic

        model = ExtractedKeyExamTopic(
            topic="소프트웨어 설계",
            frequency="매우 자주",
            importance="상",
            description="UML, 디자인 패턴, 요구사항 분석",
        )
        assert model.topic == "소프트웨어 설계"
        assert model.frequency == "매우 자주"
        assert model.importance == "상"
        assert model.description == "UML, 디자인 패턴, 요구사항 분석"

    def test_key_exam_topic_optional_description(self):
        """description은 선택 필드인지 확인."""
        from app.services.llm.service import ExtractedKeyExamTopic

        model = ExtractedKeyExamTopic(
            topic="데이터베이스",
            frequency="자주",
            importance="중",
        )
        assert model.description is None


class TestExamInfoNewFields:
    """#4: ExamInfo 스키마 신규 필드 검증."""

    def test_exam_info_schema_has_acquisition_method(self):
        """ExamInfo 스키마에 acquisition_method 필드가 있는지 확인."""
        from app.schemas.certificate import ExamInfo

        model = ExamInfo(
            subjects=["과목1"],
            exam_type="필기",
            passing_criteria="60점",
            acquisition_method="응시자격: 학력 무관",
        )
        assert model.acquisition_method == "응시자격: 학력 무관"

    def test_exam_info_schema_has_exam_criteria_url(self):
        """ExamInfo 스키마에 exam_criteria_url 필드가 있는지 확인."""
        from app.schemas.certificate import ExamInfo

        model = ExamInfo(
            subjects=["과목1"],
            exam_type="필기",
            passing_criteria="60점",
            exam_criteria_url="https://example.com",
        )
        assert model.exam_criteria_url == "https://example.com"
