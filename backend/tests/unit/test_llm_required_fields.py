"""LLM 필수 필드 반환 테스트.

TDD: LLM이 difficulty, study_period_days를 반환하지 않으면
CertificateEnrichment 생성 시 에러 발생 → 프롬프트 강화 필요.
"""

import pytest
from pydantic import ValidationError

from app.services.llm.service import CertificateEnrichment, Phase1Extraction


class TestRequiredFields:
    """필수 필드 테스트."""

    def test_certificate_enrichment_requires_difficulty(self):
        """CertificateEnrichment는 difficulty 필드가 필수임."""
        data = {
            "overview": "테스트 개요입니다.",
            # "difficulty": 3,  # 누락
            "study_period_days": 90,
            "exam_info": {},
            "career_info": {},
            "user_reviews": {},
            "study_guide": {},
            "official_sources": {},
        }

        with pytest.raises(ValidationError) as exc_info:
            CertificateEnrichment(**data)

        assert "difficulty" in str(exc_info.value)

    def test_certificate_enrichment_requires_study_period_days(self):
        """CertificateEnrichment는 study_period_days 필드가 필수임."""
        data = {
            "overview": "테스트 개요입니다.",
            "difficulty": 3,
            # "study_period_days": 90,  # 누락
            "exam_info": {},
            "career_info": {},
            "user_reviews": {},
            "study_guide": {},
            "official_sources": {},
        }

        with pytest.raises(ValidationError) as exc_info:
            CertificateEnrichment(**data)

        assert "study_period_days" in str(exc_info.value)

    def test_phase1_extraction_handles_null_difficulty(self):
        """Phase1Extraction은 difficulty=null을 기본값 3으로 변환해야 함."""
        data = {
            "overview_draft": "초안입니다.",
            "difficulty": None,  # null
            "study_period_days": 90,
            "exam_info": {"subjects": []},
            "career_info": {"use_cases": []},
            "user_reviews": {"summary": ""},
            "study_guide": {"study_methods": []},
            "official_sources": {"official_site": ""},
            "lectures": [],
        }

        result = Phase1Extraction(**data)
        assert result.difficulty == 3  # 기본값

    def test_phase1_extraction_handles_null_study_period(self):
        """Phase1Extraction은 study_period_days=null을 기본값 90으로 변환해야 함."""
        data = {
            "overview_draft": "초안입니다.",
            "difficulty": 3,
            "study_period_days": None,  # null
            "exam_info": {"subjects": []},
            "career_info": {"use_cases": []},
            "user_reviews": {"summary": ""},
            "study_guide": {"study_methods": []},
            "official_sources": {"official_site": ""},
            "lectures": [],
        }

        result = Phase1Extraction(**data)
        assert result.study_period_days == 90  # 기본값


class TestPhase2PromptContainsRequiredFields:
    """Phase 2 프롬프트에 필수 필드 강조가 포함되어야 함."""

    def test_phase2_prompt_emphasizes_required_fields(self):
        """Phase 2 프롬프트에 difficulty, study_period_days 필수 명시."""
        # LLMService 내부의 system_prompt 문자열 확인
        # _phase2_refine의 system_prompt에 필수 필드 강조가 있어야 함
        import inspect

        from app.services.llm.service import LLMService

        source = inspect.getsource(LLMService._phase2_refine)

        # 프롬프트에 difficulty와 study_period_days 필수 명시 확인
        assert "difficulty" in source.lower(), "Phase 2 프롬프트에 difficulty 언급 필요"
        assert (
            "study_period_days" in source.lower()
        ), "Phase 2 프롬프트에 study_period_days 언급 필요"

        # 필수 필드 강조 문구 확인 (수정 후 통과해야 함)
        assert (
            "필수" in source or "REQUIRED" in source.upper() or "반드시" in source
        ), "Phase 2 프롬프트에 필수 필드 강조 문구 필요"

    def test_phase2_prompt_contains_no_skip_rule(self):
        """Phase 2 프롬프트에 difficulty, study_period_days 절대생략금지 규칙 포함."""
        import inspect

        from app.services.llm.service import LLMService

        source = inspect.getsource(LLMService._phase2_refine)

        # 핵심 규칙에 절대생략금지 문구 확인
        assert "절대생략금지" in source, "핵심 규칙에 '절대생략금지' 문구 필요"

        # difficulty와 study_period_days가 핵심 규칙에 명시되어 있어야 함
        assert "difficulty 필수" in source, "핵심 규칙에 'difficulty 필수' 명시 필요"
        assert (
            "study_period_days 필수" in source
        ), "핵심 규칙에 'study_period_days 필수' 명시 필요"

        # 기본값 안내 확인
        assert (
            "정보 없으면 3 사용" in source or "기본값 3" in source
        ), "difficulty 기본값 안내 필요"
        assert (
            "정보 없으면 90 사용" in source or "기본값 90" in source
        ), "study_period_days 기본값 안내 필요"
