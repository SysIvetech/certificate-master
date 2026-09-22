"""Integration tests for minimum search query length validation.

Autocomplete API should reject queries shorter than 2 characters
to prevent excessive API calls and meaningless results.

TDD: RED phase - these tests should FAIL before implementation.
"""

from fastapi.testclient import TestClient


class TestAutocompleteMinLength:
    """Test suite for autocomplete minimum query length validation."""

    def test_autocomplete_rejects_single_character(self, client: TestClient):
        """Test that autocomplete rejects a single character query.

        Given: A single character query "정"
        When: GET /api/v1/certificates/autocomplete?q=정
        Then: It should return 422 Unprocessable Entity (validation error)
        """
        response = client.get("/api/v1/certificates/autocomplete?q=정")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_autocomplete_rejects_single_ascii_character(self, client: TestClient):
        """Test that autocomplete rejects a single ASCII character.

        Given: A single ASCII character "a"
        When: GET /api/v1/certificates/autocomplete?q=a
        Then: It should return 422 Unprocessable Entity
        """
        response = client.get("/api/v1/certificates/autocomplete?q=a")

        assert response.status_code == 422

    def test_autocomplete_accepts_two_characters(self, client: TestClient):
        """Test that autocomplete accepts a two-character query.

        Given: A two-character query "정보"
        When: GET /api/v1/certificates/autocomplete?q=정보
        Then: It should return 200 OK with results
        """
        response = client.get("/api/v1/certificates/autocomplete?q=정보")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_autocomplete_accepts_longer_query(self, client: TestClient):
        """Test that autocomplete accepts queries with 3+ characters.

        Given: A multi-character query "정보처리"
        When: GET /api/v1/certificates/autocomplete?q=정보처리
        Then: It should return 200 OK with results
        """
        response = client.get("/api/v1/certificates/autocomplete?q=정보처리")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_autocomplete_rejects_empty_query(self, client: TestClient):
        """Test that autocomplete rejects an empty query.

        Given: An empty query string
        When: GET /api/v1/certificates/autocomplete?q=
        Then: It should return 422 Unprocessable Entity
        """
        response = client.get("/api/v1/certificates/autocomplete?q=")

        assert response.status_code == 422
