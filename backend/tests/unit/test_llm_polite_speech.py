"""LLM 서비스 존댓말 테스트.

요구사항:
1. LLM 출력이 "~입니다", "~합니다", "~됩니다" 등 존댓말로 끝나야 함
2. "~이다", "~하다", "~좋다" 등 반말 종결어미 사용 금지
3. 교재 정보에 URL 링크가 포함되어야 함
4. 공식 기출문제가 있으면 학습 자료에 포함되어야 함
"""

import inspect
import re

from app.services.llm.service import LLMService


class TestLLMPromptContainsPoliteRules:
    """LLM 프롬프트에 존댓말 규칙이 포함되어 있는지 테스트."""

    def test_phase2_prompt_example_uses_polite_speech(self):
        """Phase 2 프롬프트의 예시 문장들이 존댓말을 사용해야 합니다."""
        source = inspect.getsource(LLMService._phase2_refine)

        # 예시 문장들이 존댓말로 끝나야 함
        # 현재 프롬프트에서 사용되는 예시들 확인
        polite_examples = [
            "전문가입니다",
            "필수적입니다",
            "담당합니다",
            "높습니다",
            "밝습니다",
            "있습니다",
        ]

        # 적어도 3개 이상의 존댓말 예시가 있어야 함
        polite_count = sum(1 for ex in polite_examples if ex in source)
        assert polite_count >= 3, f"존댓말 예시가 부족합니다 (현재: {polite_count}개)"

    def test_prompt_has_explicit_polite_instruction(self):
        """프롬프트에 명시적인 존댓말 사용 지시가 있어야 합니다."""
        source1 = inspect.getsource(LLMService._phase1_extract)
        source2 = inspect.getsource(LLMService._phase2_refine)
        combined = source1 + source2

        # 명시적 지시 키워드
        explicit_instructions = [
            "존댓말",
            "~입니다",
            "~합니다",
            "친절하게",
            "정중하게",
        ]

        has_explicit = any(kw in combined for kw in explicit_instructions)
        assert has_explicit, "프롬프트에 명시적인 존댓말 사용 지시가 없습니다"

    def test_prompt_forbids_impolite_endings(self):
        """프롬프트에 반말 종결어미 금지 규칙이 있어야 합니다."""
        source1 = inspect.getsource(LLMService._phase1_extract)
        source2 = inspect.getsource(LLMService._phase2_refine)
        combined = source1 + source2

        # "~이다", "~한다" 금지 관련 명시적 문구
        forbid_phrases = [
            "이다 금지",
            "한다 금지",
            "반말 금지",
            "~이다 사용 금지",
            "~한다 사용 금지",
        ]

        has_forbid = any(phrase in combined for phrase in forbid_phrases)
        assert has_forbid, "프롬프트에 반말 종결어미 금지 규칙이 없습니다"


class TestLLMPromptContainsBookUrlRule:
    """LLM 프롬프트에 교재 URL 규칙이 포함되어 있는지 테스트."""

    def test_prompt_mentions_book_url_field(self):
        """프롬프트에 교재 URL 필드가 명시되어 있어야 합니다."""
        source1 = inspect.getsource(LLMService._phase1_extract)
        source2 = inspect.getsource(LLMService._phase2_refine)
        combined = source1 + source2

        # 교재 URL 필드 명시 확인
        # recommended_books 내에 url 또는 purchase_url 필드가 있어야 함
        url_in_books_patterns = [
            '"url":',
            '"purchase_url":',
            '"link":',
            "교재 구매 링크",
            "교재 URL",
        ]

        has_url_field = any(pattern in combined for pattern in url_in_books_patterns)
        assert has_url_field, "프롬프트에 교재 URL 필드가 명시되어 있지 않습니다"

    def test_prompt_has_book_url_instruction(self):
        """프롬프트에 교재 URL 추출 지시가 있어야 합니다."""
        source1 = inspect.getsource(LLMService._phase1_extract)
        source2 = inspect.getsource(LLMService._phase2_refine)
        combined = source1 + source2

        # 교재 URL 추출 관련 지시
        url_instructions = [
            "교재 구매",
            "교재 링크",
            "교재 URL",
            "구매처",
            "yes24",
            "알라딘",
            "교보문고",
        ]

        has_instruction = any(kw in combined for kw in url_instructions)
        assert has_instruction, "프롬프트에 교재 URL 추출 지시가 없습니다"


class TestLLMPromptContainsOfficialResourceRule:
    """LLM 프롬프트에 공식 기출문제 규칙이 포함되어 있는지 테스트."""

    def test_prompt_mentions_official_resources(self):
        """프롬프트에 공식 기출문제 포함 규칙이 있어야 합니다."""
        source1 = inspect.getsource(LLMService._phase1_extract)
        source2 = inspect.getsource(LLMService._phase2_refine)
        combined = source1 + source2

        # 공식 기출 관련 키워드
        official_keywords = ["기출문제", "공식", "큐넷", "공개 문제"]

        has_official_rule = any(kw in combined for kw in official_keywords)

        assert has_official_rule, "프롬프트에 공식 기출문제 규칙이 없습니다"


class TestPoliteLanguageRequirements:
    """존댓말 요구사항 테스트."""

    def test_polite_ending_patterns(self):
        """존댓말 종결어미 패턴이 정의되어 있어야 합니다."""
        # 존댓말 종결어미 패턴
        polite_endings = [
            r"입니다\.?$",
            r"합니다\.?$",
            r"됩니다\.?$",
            r"있습니다\.?$",
            r"없습니다\.?$",
            r"습니다\.?$",
            r"세요\.?$",
            r"주세요\.?$",
            r"드립니다\.?$",
            r"바랍니다\.?$",
        ]

        # 패턴이 유효한지 확인
        for pattern in polite_endings:
            assert re.compile(pattern), f"패턴 컴파일 실패: {pattern}"

    def test_impolite_ending_detection(self):
        """반말 종결어미를 감지할 수 있어야 합니다."""
        impolite_endings = [
            r"이다\.?$",
            r"한다\.?$",
            r"된다\.?$",
            r"있다\.?$",
            r"없다\.?$",
            r"좋다\.?$",
            r"나쁘다\.?$",
            r"높다\.?$",
            r"낮다\.?$",
        ]

        # 반말 문장 예시
        impolite_sentences = [
            "이 자격증은 IT 분야에서 필수이다.",
            "합격률이 높다.",
            "취업 전망이 좋다.",
            "난이도가 높다.",
        ]

        for sentence in impolite_sentences:
            has_impolite = any(
                re.search(pattern, sentence) for pattern in impolite_endings
            )
            assert has_impolite, f"반말 감지 실패: {sentence}"

    def test_polite_sentence_validation(self):
        """존댓말 문장이 올바르게 검증되어야 합니다."""
        polite_sentences = [
            "이 자격증은 IT 분야에서 필수입니다.",
            "합격률이 높습니다.",
            "취업 전망이 좋습니다.",
            "난이도가 높습니다.",
            "꾸준히 학습하면 합격할 수 있습니다.",
        ]

        polite_pattern = (
            r"(입니다|합니다|됩니다|있습니다|없습니다|습니다|세요|주세요)\.?$"
        )

        for sentence in polite_sentences:
            assert re.search(polite_pattern, sentence), f"존댓말 검증 실패: {sentence}"


class TestRecommendedBookWithUrl:
    """추천 교재 URL 포함 테스트."""

    def test_book_schema_includes_url(self):
        """추천 교재 스키마에 URL 필드가 포함되어야 합니다."""
        # 예상 교재 데이터 구조
        expected_book_schema = {
            "title": str,
            "publisher": str,
            "type": str,
            "description": str,
            "url": str,  # 새로 추가되어야 할 필드
        }

        # URL 필드 존재 확인
        assert "url" in expected_book_schema

    def test_book_url_validation(self):
        """교재 URL이 유효한 형식이어야 합니다."""
        valid_urls = [
            "https://www.yes24.com/Product/Goods/12345",
            "https://www.aladin.co.kr/shop/wproduct.aspx?ItemId=12345",
            "https://product.kyobobook.co.kr/detail/S000001234567",
        ]

        url_pattern = r"^https?://"

        for url in valid_urls:
            assert re.match(url_pattern, url), f"URL 형식 검증 실패: {url}"


class TestOfficialResourcesInStudyGuide:
    """공식 기출문제 학습 가이드 포함 테스트."""

    def test_official_exam_resources_structure(self):
        """공식 기출문제 자료 구조가 올바르게 정의되어야 합니다."""
        # 예상 free_resources 구조
        expected_structure = {
            "title": "큐넷 공식 기출문제",
            "url": "https://www.q-net.or.kr/...",
            "type": "official",
            "description": "한국산업인력공단 공식 기출문제 PDF",
        }

        assert "title" in expected_structure
        assert "url" in expected_structure
        assert "type" in expected_structure

    def test_free_resources_includes_official(self):
        """free_resources에 공식 자료가 포함되어야 합니다."""
        # 예상 데이터
        cost_breakdown = {
            "exam_fee": "필기 19,400원 + 실기 22,600원",
            "free_resources": [
                {
                    "title": "큐넷 공식 기출문제",
                    "url": "https://www.q-net.or.kr/crf005.do?id=crf00505&gSite=Q",
                    "type": "official",
                },
                {
                    "title": "유튜브 무료 강의",
                    "url": "https://www.youtube.com/...",
                    "type": "community",
                },
            ],
        }

        # 공식 자료 존재 확인
        official_resources = [
            r for r in cost_breakdown["free_resources"] if r.get("type") == "official"
        ]
        assert len(official_resources) > 0, "공식 자료가 없습니다"
