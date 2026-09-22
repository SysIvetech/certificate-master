"""공백 분할 + character 2-gram 토큰화 테스트."""

from app.services.search.tokenizer import tokenize


class TestTokenize:
    def test_splits_by_whitespace(self):
        tokens = tokenize("정보처리기사 자격증")
        assert "정보처리기사" in tokens
        assert "자격증" in tokens

    def test_generates_bigrams(self):
        tokens = tokenize("정보처리기사")
        assert "정보" in tokens
        assert "보처" in tokens
        assert "처리" in tokens
        assert "리기" in tokens
        assert "기사" in tokens

    def test_includes_original_word_and_bigrams(self):
        tokens = tokenize("전기기사 자격증")
        assert "전기기사" in tokens
        assert "자격증" in tokens
        assert "전기" in tokens
        assert "기기" in tokens
        assert "기사" in tokens

    def test_empty_string_returns_empty_list(self):
        assert tokenize("") == []

    def test_single_char_word_no_bigram(self):
        tokens = tokenize("IT 보안")
        assert "IT" in tokens
        assert "보안" in tokens

    def test_removes_duplicates(self):
        tokens = tokenize("기사 기사")
        assert tokens.count("기사") == 1

    def test_strips_whitespace(self):
        tokens = tokenize("  정보처리기사  ")
        assert "정보처리기사" in tokens
