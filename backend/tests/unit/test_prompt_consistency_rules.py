"""LLM 프롬프트에 difficulty-study_period_days 정합성 규칙이 포함되어 있는지 검증."""

import inspect

from app.services.llm.service import LLMService


class TestPhase1PromptConsistencyRules:
    """Phase 1 프롬프트에 정합성 규칙이 포함되어 있는지 검증."""

    def setup_method(self):
        """_phase1_extract 메서드의 소스 코드를 가져온다."""
        self.source = inspect.getsource(LLMService._phase1_extract)

    def test_prompt_contains_consistency_table(self):
        """difficulty별 study_period_days 허용 범위 테이블이 프롬프트에 포함."""
        # 각 난이도별 범위가 명시되어야 함
        assert "difficulty=1" in self.source or "난이도 1" in self.source
        assert "difficulty=5" in self.source or "난이도 5" in self.source

    def test_prompt_mentions_period_range_for_each_difficulty(self):
        """5개 난이도 각각에 대해 일수 범위가 명시되어야 한다."""
        # 각 난이도의 기간 범위 키워드 확인
        for level in range(1, 6):
            assert (
                f"difficulty={level}" in self.source
                or f"난이도={level}" in self.source
                or f"난이도 {level}" in self.source
            ), f"난이도 {level}에 대한 범위가 프롬프트에 없음"

    def test_prompt_warns_about_consistency(self):
        """정합성 관련 경고/규칙 키워드가 포함되어야 한다."""
        keywords = ["정합성", "일치", "범위"]
        assert any(
            kw in self.source for kw in keywords
        ), f"정합성 관련 키워드({keywords}) 중 하나가 프롬프트에 없음"


class TestPhase2PromptConsistencyRules:
    """Phase 2 프롬프트에 정합성 규칙이 포함되어 있는지 검증."""

    def setup_method(self):
        """_phase2_refine 메서드의 소스 코드를 가져온다."""
        self.source = inspect.getsource(LLMService._phase2_refine)

    def test_prompt_contains_consistency_rule(self):
        """Phase 2 프롬프트에도 정합성 규칙이 포함되어야 한다."""
        keywords = ["정합성", "일치", "범위"]
        assert any(
            kw in self.source for kw in keywords
        ), f"Phase 2 프롬프트에 정합성 관련 키워드({keywords}) 중 하나가 없음"

    def test_prompt_mentions_difficulty_period_relationship(self):
        """difficulty와 study_period_days의 관계가 명시되어야 한다."""
        assert (
            "difficulty" in self.source and "study_period_days" in self.source
        ), "Phase 2 프롬프트에 difficulty-study_period_days 관계가 명시되지 않음"
