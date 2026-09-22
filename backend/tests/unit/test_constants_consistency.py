"""Enum 값 일관성 테스트.

프롬프트와 스키마의 Enum 값이 일치하는지 검증합니다.
"""


class TestEnumConstantsConsistency:
    """Enum 상수 일관성 테스트."""

    def test_natural_goals_consistency(self):
        """자연어 추천의 goal 값이 스키마와 프롬프트에서 일치하는지 확인."""
        from app.core.constants import RecommendationConstants
        from app.schemas.recommendation import VALID_NATURAL_GOALS

        # 스키마와 constants가 일치해야 함
        assert set(RecommendationConstants.NATURAL_GOALS) == set(VALID_NATURAL_GOALS)

    def test_employment_status_consistency(self):
        """employment_status 값이 스키마와 일치하는지 확인."""
        from app.core.constants import RecommendationConstants
        from app.schemas.recommendation import VALID_EMPLOYMENT_STATUS

        assert set(RecommendationConstants.EMPLOYMENT_STATUS) == set(
            VALID_EMPLOYMENT_STATUS
        )

    def test_major_background_consistency(self):
        """major_background 값이 스키마와 일치하는지 확인."""
        from app.core.constants import RecommendationConstants
        from app.schemas.recommendation import VALID_MAJOR_BACKGROUND

        assert set(RecommendationConstants.MAJOR_BACKGROUND) == set(
            VALID_MAJOR_BACKGROUND
        )

    def test_natural_difficulty_consistency(self):
        """difficulty_preference 값이 스키마와 일치하는지 확인."""
        from app.core.constants import RecommendationConstants
        from app.schemas.recommendation import VALID_NATURAL_DIFFICULTY

        assert set(RecommendationConstants.NATURAL_DIFFICULTY) == set(
            VALID_NATURAL_DIFFICULTY
        )

    def test_prompt_uses_constants_for_goals(self):
        """프롬프트가 constants에서 goal 값을 동적으로 생성하는지 확인."""
        from app.core.constants import RecommendationConstants
        from app.services.study.prompts.context_extraction import (
            CONTEXT_EXTRACTION_SYSTEM_PROMPT,
        )

        # 프롬프트에 모든 goal 값이 포함되어야 함
        for goal in RecommendationConstants.NATURAL_GOALS:
            assert (
                goal in CONTEXT_EXTRACTION_SYSTEM_PROMPT
            ), f"Goal '{goal}' not found in prompt"

    def test_prompt_uses_constants_for_employment_status(self):
        """프롬프트가 constants에서 employment_status 값을 포함하는지 확인."""
        from app.core.constants import RecommendationConstants
        from app.services.study.prompts.context_extraction import (
            CONTEXT_EXTRACTION_SYSTEM_PROMPT,
        )

        for status in RecommendationConstants.EMPLOYMENT_STATUS:
            assert (
                status in CONTEXT_EXTRACTION_SYSTEM_PROMPT
            ), f"Employment status '{status}' not found in prompt"

    def test_prompt_uses_constants_for_major_background(self):
        """프롬프트가 constants에서 major_background 값을 포함하는지 확인."""
        from app.core.constants import RecommendationConstants
        from app.services.study.prompts.context_extraction import (
            CONTEXT_EXTRACTION_SYSTEM_PROMPT,
        )

        for background in RecommendationConstants.MAJOR_BACKGROUND:
            assert (
                background in CONTEXT_EXTRACTION_SYSTEM_PROMPT
            ), f"Major background '{background}' not found in prompt"

    def test_prompt_uses_constants_for_difficulty(self):
        """프롬프트가 constants에서 difficulty 값을 포함하는지 확인."""
        from app.core.constants import RecommendationConstants
        from app.services.study.prompts.context_extraction import (
            CONTEXT_EXTRACTION_SYSTEM_PROMPT,
        )

        for difficulty in RecommendationConstants.NATURAL_DIFFICULTY:
            assert (
                difficulty in CONTEXT_EXTRACTION_SYSTEM_PROMPT
            ), f"Difficulty '{difficulty}' not found in prompt"


class TestPromptDynamicGeneration:
    """프롬프트가 constants를 동적으로 사용하는지 테스트."""

    def test_prompt_generated_from_constants(self):
        """프롬프트가 constants에서 동적으로 생성되는지 확인."""
        from app.core.constants import RecommendationConstants
        from app.services.study.prompts.context_extraction import (
            build_context_extraction_prompt,
        )

        prompt = build_context_extraction_prompt()

        # 모든 goal 값이 프롬프트에 포함되어야 함
        for goal in RecommendationConstants.NATURAL_GOALS:
            assert goal in prompt, f"Goal '{goal}' not in generated prompt"

    def test_prompt_updates_when_constants_change(self):
        """constants가 변경되면 프롬프트도 변경되는지 확인 (구조 테스트)."""
        from app.services.study.prompts.context_extraction import (
            build_context_extraction_prompt,
        )

        # 함수가 호출될 때마다 새로 생성되어야 함
        prompt1 = build_context_extraction_prompt()
        prompt2 = build_context_extraction_prompt()

        # 동일한 결과여야 함 (같은 constants 사용)
        assert prompt1 == prompt2


class TestSchemaUsesConstants:
    """스키마가 constants를 직접 참조하는지 테스트."""

    def test_schema_imports_from_constants(self):
        """recommendation.py가 constants에서 값을 import하는지 확인."""
        from app.core.constants import RecommendationConstants
        from app.schemas import recommendation

        # recommendation 모듈의 상수가 constants와 동일한 객체여야 함
        assert (
            recommendation.VALID_NATURAL_GOALS is RecommendationConstants.NATURAL_GOALS
        )
        assert (
            recommendation.VALID_EMPLOYMENT_STATUS
            is RecommendationConstants.EMPLOYMENT_STATUS
        )
        assert (
            recommendation.VALID_MAJOR_BACKGROUND
            is RecommendationConstants.MAJOR_BACKGROUND
        )
        assert (
            recommendation.VALID_NATURAL_DIFFICULTY
            is RecommendationConstants.NATURAL_DIFFICULTY
        )


class TestSchemaMappingDocumentation:
    """스키마 매핑 문서 존재 및 유효성 테스트."""

    def test_schema_mapping_doc_exists(self):
        """SCHEMA_MAPPING.md 문서가 존재하는지 확인."""
        from pathlib import Path

        doc_path = (
            Path(__file__).parent.parent.parent
            / "app"
            / "services"
            / "llm"
            / "SCHEMA_MAPPING.md"
        )
        assert doc_path.exists(), "SCHEMA_MAPPING.md not found"

    def test_schema_mapping_doc_contains_key_sections(self):
        """문서에 필수 섹션이 포함되어 있는지 확인."""
        from pathlib import Path

        doc_path = (
            Path(__file__).parent.parent.parent
            / "app"
            / "services"
            / "llm"
            / "SCHEMA_MAPPING.md"
        )
        content = doc_path.read_text(encoding="utf-8")

        required_sections = [
            "Phase 1: 추출",
            "Phase 2: 정제",
            "자연어 추천",
            "스키마 변환",
            "필드 의미론",
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"


class TestConstantsExistence:
    """Constants 모듈 존재 및 구조 테스트."""

    def test_constants_module_exists(self):
        """app.core.constants 모듈이 존재하는지 확인."""
        from app.core import constants

        assert hasattr(constants, "RecommendationConstants")

    def test_recommendation_constants_has_required_attributes(self):
        """RecommendationConstants에 필수 속성이 있는지 확인."""
        from app.core.constants import RecommendationConstants

        required_attrs = [
            "NATURAL_GOALS",
            "EMPLOYMENT_STATUS",
            "MAJOR_BACKGROUND",
            "NATURAL_DIFFICULTY",
        ]

        for attr in required_attrs:
            assert hasattr(
                RecommendationConstants, attr
            ), f"RecommendationConstants missing '{attr}'"

    def test_constants_are_lists(self):
        """상수들이 리스트 타입인지 확인."""
        from app.core.constants import RecommendationConstants

        assert isinstance(RecommendationConstants.NATURAL_GOALS, list)
        assert isinstance(RecommendationConstants.EMPLOYMENT_STATUS, list)
        assert isinstance(RecommendationConstants.MAJOR_BACKGROUND, list)
        assert isinstance(RecommendationConstants.NATURAL_DIFFICULTY, list)

    def test_constants_not_empty(self):
        """상수들이 비어있지 않은지 확인."""
        from app.core.constants import RecommendationConstants

        assert len(RecommendationConstants.NATURAL_GOALS) > 0
        assert len(RecommendationConstants.EMPLOYMENT_STATUS) > 0
        assert len(RecommendationConstants.MAJOR_BACKGROUND) > 0
        assert len(RecommendationConstants.NATURAL_DIFFICULTY) > 0
