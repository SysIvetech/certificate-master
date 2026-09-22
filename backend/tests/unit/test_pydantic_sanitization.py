"""Pydantic validator를 통한 자동 정제 테스트.

서비스 코드가 아닌 Pydantic 모델에서 데이터 정제가 이루어지는지 검증합니다.
"""


class TestExtractedStudyGuideValidator:
    """ExtractedStudyGuide 모델의 recommended_books 자동 정제 테스트."""

    def test_recommended_books_filters_placeholder_titles(self):
        """placeholder 제목이 자동으로 필터링되는지 확인."""
        from app.services.llm.service import ExtractedStudyGuide

        data = {
            "recommended_books": [
                {"title": "교재명", "publisher": "출판사"},  # placeholder - 제거
                {"title": "실제 교재", "publisher": "실제 출판사"},  # 유지
            ]
        }

        guide = ExtractedStudyGuide(**data)

        assert len(guide.recommended_books) == 1
        assert guide.recommended_books[0]["title"] == "실제 교재"

    def test_recommended_books_removes_empty_titles(self):
        """빈 제목이 자동으로 필터링되는지 확인."""
        from app.services.llm.service import ExtractedStudyGuide

        data = {
            "recommended_books": [
                {"title": "", "publisher": "출판사"},  # 빈 제목 - 제거
                {"title": "유효한 책", "publisher": "출판사"},  # 유지
            ]
        }

        guide = ExtractedStudyGuide(**data)

        assert len(guide.recommended_books) == 1
        assert guide.recommended_books[0]["title"] == "유효한 책"

    def test_recommended_books_removes_missing_publisher(self):
        """출판사가 없는 항목이 자동으로 필터링되는지 확인."""
        from app.services.llm.service import ExtractedStudyGuide

        data = {
            "recommended_books": [
                {"title": "책1", "publisher": ""},  # 빈 출판사 - 제거
                {"title": "책2"},  # 출판사 없음 - 제거
                {"title": "책3", "publisher": "출판사"},  # 유지
            ]
        }

        guide = ExtractedStudyGuide(**data)

        assert len(guide.recommended_books) == 1
        assert guide.recommended_books[0]["title"] == "책3"

    def test_recommended_books_deduplicates(self):
        """중복 항목이 자동으로 제거되는지 확인."""
        from app.services.llm.service import ExtractedStudyGuide

        data = {
            "recommended_books": [
                {"title": "같은 책", "publisher": "같은 출판사"},
                {"title": "같은 책", "publisher": "같은 출판사"},  # 중복 - 제거
                {"title": "다른 책", "publisher": "다른 출판사"},
            ]
        }

        guide = ExtractedStudyGuide(**data)

        assert len(guide.recommended_books) == 2
        titles = [b["title"] for b in guide.recommended_books]
        assert "같은 책" in titles
        assert "다른 책" in titles

    def test_recommended_books_handles_none(self):
        """None 값이 빈 리스트로 변환되는지 확인."""
        from app.services.llm.service import ExtractedStudyGuide

        data = {"recommended_books": None}

        guide = ExtractedStudyGuide(**data)

        assert guide.recommended_books == []

    def test_recommended_books_preserves_valid_entries(self):
        """유효한 항목이 모두 유지되는지 확인."""
        from app.services.llm.service import ExtractedStudyGuide

        data = {
            "recommended_books": [
                {
                    "title": "전기기사 필기 기본서",
                    "publisher": "성안당",
                    "type": "기본서",
                    "description": "체계적인 이론 정리",
                },
                {
                    "title": "전기기사 기출문제집",
                    "publisher": "성안당",
                    "type": "문제집",
                },
            ]
        }

        guide = ExtractedStudyGuide(**data)

        assert len(guide.recommended_books) == 2
        assert guide.recommended_books[0]["title"] == "전기기사 필기 기본서"
        assert guide.recommended_books[0]["description"] == "체계적인 이론 정리"


class TestPlaceholderTitlesList:
    """placeholder 제목 목록 테스트."""

    def test_all_placeholder_titles_filtered(self):
        """모든 알려진 placeholder 제목이 필터링되는지 확인."""
        from app.services.llm.service import ExtractedStudyGuide

        # LLM이 정보 없을 때 생성하는 placeholder들
        placeholder_titles = [
            "교재명",
            "책 제목",
            "도서명",
            "추천 교재",
            "교재",
            "기본서",
            "책",
            "수험서",
            "문제집",
            "기출문제집",
            "요약집",
        ]

        for placeholder in placeholder_titles:
            data = {
                "recommended_books": [
                    {"title": placeholder, "publisher": "출판사"},
                ]
            }

            guide = ExtractedStudyGuide(**data)

            assert (
                len(guide.recommended_books) == 0
            ), f"Placeholder '{placeholder}' should be filtered"
