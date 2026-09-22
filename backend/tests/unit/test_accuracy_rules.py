"""정보 정확성 규칙 테스트.

요구사항:
1. 시험 일정 정보는 공식 출처에서 확인된 경우만 저장
2. 연봉 정보는 신뢰할 수 있는 출처 기반으로만 표시
"""

import inspect

from app.services.llm.service import LLMService


class TestExamScheduleAccuracyRules:
    """시험 일정 정확성 규칙 테스트."""

    def test_prompt_requires_official_source_for_exam_schedule(self):
        """시험 일정은 공식 출처에서 확인된 경우만 저장해야 합니다."""
        source1 = inspect.getsource(LLMService._phase1_extract)
        source2 = inspect.getsource(LLMService._phase2_refine)
        combined = source1 + source2

        # 시험 일정 관련 정확성 규칙 키워드
        accuracy_keywords = [
            "공식 출처",
            "크롤링",
            "확인되지 않으면",
            "null로",
            "추측 금지",
        ]

        # 적어도 2개 이상의 정확성 규칙 키워드가 있어야 함
        has_accuracy_rule = sum(1 for kw in accuracy_keywords if kw in combined) >= 2
        assert has_accuracy_rule, "프롬프트에 시험 일정 정확성 규칙이 없습니다"

    def test_prompt_forbids_guessing_exam_dates(self):
        """시험 일정을 추측하면 안 됩니다."""
        source1 = inspect.getsource(LLMService._phase1_extract)
        source2 = inspect.getsource(LLMService._phase2_refine)
        combined = source1 + source2

        # 추측 금지 관련 키워드
        forbid_keywords = [
            "추측하지",
            "예상하지",
            "짐작하지",
            "추정하지",
        ]

        has_forbid = any(kw in combined for kw in forbid_keywords)
        assert has_forbid, "프롬프트에 시험 일정 추측 금지 규칙이 없습니다"


class TestSalaryAccuracyRules:
    """연봉 정보 정확성 규칙 테스트."""

    def test_prompt_requires_reliable_source_for_salary(self):
        """연봉 정보는 신뢰할 수 있는 출처 기반이어야 합니다."""
        source1 = inspect.getsource(LLMService._phase1_extract)
        source2 = inspect.getsource(LLMService._phase2_refine)
        combined = source1 + source2

        # 연봉 출처 관련 키워드
        source_keywords = [
            "통계청",
            "고용노동부",
            "워크넷",
            "잡코리아",
            "사람인",
            "채용공고",
            "공식 통계",
        ]

        has_source_rule = any(kw in combined for kw in source_keywords)
        assert has_source_rule, "프롬프트에 연봉 출처 규칙이 없습니다"

    def test_prompt_mentions_salary_range_format(self):
        """연봉은 범위 형식으로 표시해야 합니다."""
        source1 = inspect.getsource(LLMService._phase1_extract)
        source2 = inspect.getsource(LLMService._phase2_refine)
        combined = source1 + source2

        # 범위 형식 관련 키워드
        range_keywords = [
            "범위",
            "~",
            "연봉 범위",
            "신입 기준",
            "경력 기준",
        ]

        has_range_rule = any(kw in combined for kw in range_keywords)
        assert has_range_rule, "프롬프트에 연봉 범위 형식 규칙이 없습니다"
