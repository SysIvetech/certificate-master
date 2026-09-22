"""Tests for CSV parsing script.

Following TDD: These tests are written FIRST before implementation.
Expected result: Tests will FAIL until parse_csv.py is implemented.
"""

import json
import tempfile
from pathlib import Path

import pytest


class TestParseCsv:
    """Test suite for CSV parsing functionality."""

    @pytest.fixture
    def sample_csv_content(self) -> str:
        """Sample CSV content for testing."""
        return """자격구분코드,자격구분명,계열명,종목명
S,국가전문자격,세무사,세무사
S,국가전문자격,관세사,관세사
T,국가기술자격,정보처리,정보처리기사
"""

    @pytest.fixture
    def temp_csv_file(self, sample_csv_content: str) -> Path:
        """Create a temporary CSV file for testing."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8-sig"
        ) as f:
            f.write(sample_csv_content)
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()

    def test_parse_csv_returns_list(self, temp_csv_file: Path) -> None:
        """Test that parse_csv returns a list of certificates."""
        from scripts.parse_csv import parse_csv_to_json

        result = parse_csv_to_json(temp_csv_file)

        assert isinstance(result, list)

    def test_parse_csv_correct_count(self, temp_csv_file: Path) -> None:
        """Test that parse_csv returns correct number of certificates."""
        from scripts.parse_csv import parse_csv_to_json

        result = parse_csv_to_json(temp_csv_file)

        assert len(result) == 3

    def test_parse_csv_certificate_structure(self, temp_csv_file: Path) -> None:
        """Test that each certificate has required fields."""
        from scripts.parse_csv import parse_csv_to_json

        result = parse_csv_to_json(temp_csv_file)

        required_fields = ["categories", "series", "title", "raw_id"]
        for cert in result:
            for field in required_fields:
                assert field in cert, f"Missing field: {field}"
            # categories 구조 검증
            assert isinstance(cert["categories"], list)
            assert len(cert["categories"]) > 0
            assert "code" in cert["categories"][0]
            assert "name" in cert["categories"][0]

    def test_parse_csv_first_certificate_values(self, temp_csv_file: Path) -> None:
        """Test that first certificate has correct values."""
        from scripts.parse_csv import parse_csv_to_json

        result = parse_csv_to_json(temp_csv_file)

        first_cert = result[0]
        assert first_cert["categories"][0]["code"] == "S"
        assert first_cert["categories"][0]["name"] == "국가전문자격"
        assert first_cert["series"] == "세무사"
        assert first_cert["title"] == "세무사"
        assert first_cert["raw_id"] == "S_세무사"

    def test_parse_csv_generates_correct_raw_id(self, temp_csv_file: Path) -> None:
        """Test that raw_id is generated correctly from code and title."""
        from scripts.parse_csv import parse_csv_to_json

        result = parse_csv_to_json(temp_csv_file)

        for cert in result:
            code = cert["categories"][0]["code"]
            expected_raw_id = f"{code}_{cert['title']}"
            assert cert["raw_id"] == expected_raw_id

    def test_save_to_json_creates_file(self, temp_csv_file: Path) -> None:
        """Test that save_to_json creates a valid JSON file."""
        from scripts.parse_csv import parse_csv_to_json, save_to_json

        certificates = parse_csv_to_json(temp_csv_file)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            save_to_json(certificates, output_path)

            assert output_path.exists()

            with open(output_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            assert loaded == certificates
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_parse_csv_handles_empty_file(self) -> None:
        """Test that parse_csv handles empty CSV gracefully."""
        from scripts.parse_csv import parse_csv_to_json

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8-sig"
        ) as f:
            f.write("자격구분코드,자격구분명,계열명,종목명\n")
            temp_path = Path(f.name)

        try:
            result = parse_csv_to_json(temp_path)
            assert result == []
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_parse_csv_strips_whitespace(self) -> None:
        """Test that parse_csv strips whitespace from values."""
        from scripts.parse_csv import parse_csv_to_json

        csv_content = """자격구분코드,자격구분명,계열명,종목명
S, 국가전문자격 , 세무사 , 세무사
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8-sig"
        ) as f:
            f.write(csv_content)
            temp_path = Path(f.name)

        try:
            result = parse_csv_to_json(temp_path)
            cert = result[0]

            assert cert["categories"][0]["name"] == "국가전문자격"
            assert cert["series"] == "세무사"
            assert cert["title"] == "세무사"
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_parse_csv_merges_duplicate_titles(self) -> None:
        """Test that certificates with same title are merged with multiple categories."""
        from scripts.parse_csv import parse_csv_to_json

        # 같은 종목명(정보처리기사)이 두 개의 자격구분을 가짐
        csv_content = """자격구분코드,자격구분명,계열명,종목명
T,국가기술자격,정보처리,정보처리기사
C,과정평가형자격,정보처리,정보처리기사
S,국가전문자격,세무사,세무사
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8-sig"
        ) as f:
            f.write(csv_content)
            temp_path = Path(f.name)

        try:
            result = parse_csv_to_json(temp_path)

            # 중복이 병합되어 2개만 있어야 함
            assert len(result) == 2

            # 정보처리기사는 2개의 카테고리를 가져야 함
            info_cert = next(c for c in result if c["title"] == "정보처리기사")
            assert len(info_cert["categories"]) == 2
            assert {"code": "T", "name": "국가기술자격"} in info_cert["categories"]
            assert {"code": "C", "name": "과정평가형자격"} in info_cert["categories"]

            # raw_id는 첫 번째 카테고리 코드 사용
            assert info_cert["raw_id"] == "T_정보처리기사"

            # 세무사는 1개의 카테고리만 가져야 함
            tax_cert = next(c for c in result if c["title"] == "세무사")
            assert len(tax_cert["categories"]) == 1
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_parse_csv_no_duplicate_categories(self) -> None:
        """Test that same category is not added twice for same title."""
        from scripts.parse_csv import parse_csv_to_json

        # 같은 종목명과 같은 카테고리가 중복으로 있는 경우
        csv_content = """자격구분코드,자격구분명,계열명,종목명
T,국가기술자격,정보처리,정보처리기사
T,국가기술자격,정보처리,정보처리기사
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8-sig"
        ) as f:
            f.write(csv_content)
            temp_path = Path(f.name)

        try:
            result = parse_csv_to_json(temp_path)

            # 완전히 동일한 행은 1개로 병합
            assert len(result) == 1
            assert len(result[0]["categories"]) == 1
        finally:
            if temp_path.exists():
                temp_path.unlink()
