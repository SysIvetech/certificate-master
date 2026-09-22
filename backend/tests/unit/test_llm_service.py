"""Unit tests for LLMService helpers."""

from app.services.llm_service import LLMService


def test_sanitize_recommended_books_filters_placeholders_and_empty():
    books = [
        {"title": "교재명", "publisher": "시대에듀", "type": "필기"},
        {"title": "정보처리기사 필기", "publisher": "시대에듀", "type": "필기"},
        {"title": "", "publisher": "출판사", "description": "설명"},
        {"title": "기출문제집", "description": "요약"},
    ]

    sanitized = LLMService.sanitize_recommended_books(books)

    assert len(sanitized) == 1
    assert sanitized[0]["title"] == "정보처리기사 필기"


def test_sanitize_recommended_books_requires_details():
    books = [
        {"title": "정보처리기사 필기"},
        {"title": "정보처리기사 실기", "type": "실기"},
    ]

    sanitized = LLMService.sanitize_recommended_books(books)

    assert sanitized == []


def test_sanitize_recommended_books_deduplicates():
    books = [
        {"title": "정보처리기사 필기", "publisher": "시대에듀"},
        {
            "title": "정보처리기사 필기",
            "publisher": "시대에듀",
            "description": "개정판",
        },
        {"title": "정보처리기사 필기", "publisher": "다른출판사"},
    ]

    sanitized = LLMService.sanitize_recommended_books(books)

    assert len(sanitized) == 2
    assert sanitized[0]["publisher"] == "시대에듀"
    assert sanitized[1]["publisher"] == "다른출판사"
