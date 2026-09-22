"""Integration tests for Certificates API endpoints.

These tests follow TDD principles:
1. Write a failing test (Red)
2. Write minimal code to pass the test (Green)
3. Refactor if needed (Refactor)
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

# test_supabase_client 는 SQLAlchemy 기반 호환 래퍼 (타입 표기용 별칭)
Client = Any


class TestCertificatesSearch:
    """Test suite for certificate search endpoint."""

    def test_search_certificates_without_filters(self, client: TestClient):
        """Test searching certificates without any filters.

        Given: A database with certificates
        When: GET /api/v1/certificates/search is called without filters
        Then: It should return a paginated list of certificates
        """
        response = client.get("/api/v1/certificates/search")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "has_more" in data

        # Verify pagination defaults
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert isinstance(data["items"], list)

    def test_search_certificates_with_keyword(self, client: TestClient):
        """Test searching certificates with a keyword.

        Given: A database with certificates
        When: GET /api/v1/certificates/search?q=정보처리 is called
        Then: It should return certificates matching the keyword
        """
        response = client.get("/api/v1/certificates/search?q=정보처리")

        assert response.status_code == 200
        data = response.json()

        # Should return some results
        assert isinstance(data["items"], list)

        # If results exist, verify they contain the keyword
        if data["items"]:
            # At least one should match
            found = any(
                "정보처리" in item["title"]
                or (
                    "series" in item and item["series"] and "정보처리" in item["series"]
                )
                for item in data["items"]
            )
            assert found, "Search results should contain the keyword"

    def test_search_certificates_with_category_filter(self, client: TestClient):
        """Test filtering certificates by category.

        Given: A database with certificates
        When: GET /api/v1/certificates/search?categories=국가기술자격 is called
        Then: All returned certificates should have the specified category
        """
        category = "국가기술자격"
        response = client.get(f"/api/v1/certificates/search?categories={category}")

        assert response.status_code == 200
        data = response.json()

        # If results exist, all should have the correct category
        if data["items"]:
            for item in data["items"]:
                # categories 배열에서 해당 카테고리가 있는지 확인
                category_names = [cat["name"] for cat in item["categories"]]
                assert category in category_names

    def test_search_certificates_with_pagination(self, client: TestClient):
        """Test certificate search pagination.

        Given: A database with many certificates
        When: GET /api/v1/certificates/search?page=1&page_size=5 is called
        Then: It should return exactly 5 items (if available)
        """
        response = client.get("/api/v1/certificates/search?page=1&page_size=5")

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 5

        # Should return at most 5 items
        assert len(data["items"]) <= 5


class TestCertificatesRetrieve:
    """Test suite for certificate retrieval endpoints."""

    def test_get_certificate_by_id_success(
        self, client: TestClient, test_supabase_client: Client
    ):
        """Test retrieving a certificate by UUID.

        Given: A certificate exists in the database
        When: GET /api/v1/certificates/{id} is called with valid UUID
        Then: It should return the certificate details
        """
        # First, get any certificate to test with
        certs = (
            test_supabase_client.table("certificates").select("id").limit(1).execute()
        )

        if not certs.data:
            pytest.skip("No certificates in database to test with")

        cert_id = certs.data[0]["id"]
        response = client.get(f"/api/v1/certificates/{cert_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify certificate structure
        assert data["id"] == cert_id
        assert "title" in data
        assert "categories" in data
        assert isinstance(data["categories"], list)

    def test_get_certificate_by_id_not_found(self, client: TestClient):
        """Test retrieving a non-existent certificate.

        Given: A certificate UUID that doesn't exist
        When: GET /api/v1/certificates/{id} is called
        Then: It should return 404 Not Found
        """
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/certificates/{fake_uuid}")

        assert response.status_code == 404
        assert "detail" in response.json()

    def test_get_certificate_by_raw_id_success(
        self, client: TestClient, test_supabase_client: Client
    ):
        """Test retrieving a certificate by raw_id.

        Given: A certificate exists in the database
        When: GET /api/v1/certificates/raw/{raw_id} is called
        Then: It should return the certificate details
        """
        # Get a certificate with known raw_id
        certs = (
            test_supabase_client.table("certificates")
            .select("raw_id")
            .limit(1)
            .execute()
        )

        if not certs.data:
            pytest.skip("No certificates in database to test with")

        raw_id = certs.data[0]["raw_id"]
        response = client.get(f"/api/v1/certificates/raw/{raw_id}")

        assert response.status_code == 200
        data = response.json()

        assert data["raw_id"] == raw_id


class TestCertificatesCategories:
    """Test suite for certificate categories endpoint."""

    def test_get_categories_success(self, client: TestClient):
        """Test retrieving all certificate categories.

        Given: A database with certificates
        When: GET /api/v1/certificates/categories is called
        Then: It should return a list of unique categories with code and name
        """
        response = client.get("/api/v1/certificates/categories")

        assert response.status_code == 200
        data = response.json()

        # Should return a list of objects
        assert isinstance(data, list)

        # If data exists, check they have code and name
        if data:
            for cat in data:
                assert "code" in cat
                assert "name" in cat

            # Names should be unique
            names = [cat["name"] for cat in data]
            assert len(names) == len(set(names))


class TestCertificatesUpdate:
    """Test suite for certificate update endpoint."""

    def test_update_certificate_success(
        self, client: TestClient, test_supabase_client: Client, clean_test_certificates
    ):
        """Test updating a certificate with enriched data.

        Given: A certificate exists in the database
        When: PATCH /api/v1/certificates/{id} is called with update data
        Then: The certificate should be updated successfully
        """
        # Create a test certificate
        test_cert = {
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "테스트",
            "title": "테스트자격증",
            "raw_id": "TEST_update_test",
        }

        insert_result = (
            test_supabase_client.table("certificates").insert(test_cert).execute()
        )
        cert_id = insert_result.data[0]["id"]

        # Update the certificate
        update_data = {
            "overview": "테스트 자격증 개요입니다.",
            "difficulty": 3,
            "study_period_days": 90,
        }

        response = client.patch(f"/api/v1/certificates/{cert_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()

        # Verify updated fields
        assert data["overview"] == update_data["overview"]
        assert data["difficulty"] == update_data["difficulty"]
        assert data["study_period_days"] == update_data["study_period_days"]

    def test_update_certificate_not_found(self, client: TestClient):
        """Test updating a non-existent certificate.

        Given: A certificate UUID that doesn't exist
        When: PATCH /api/v1/certificates/{id} is called
        Then: It should return 404 Not Found
        """
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        update_data = {"overview": "Test"}

        response = client.patch(f"/api/v1/certificates/{fake_uuid}", json=update_data)

        assert response.status_code == 404

    def test_update_certificate_empty_data(
        self, client: TestClient, test_supabase_client: Client
    ):
        """Test updating a certificate with no data.

        Given: A certificate exists in the database
        When: PATCH /api/v1/certificates/{id} is called with empty data
        Then: It should return 400 Bad Request
        """
        # Get any certificate
        certs = (
            test_supabase_client.table("certificates").select("id").limit(1).execute()
        )

        if not certs.data:
            pytest.skip("No certificates in database to test with")

        cert_id = certs.data[0]["id"]

        response = client.patch(f"/api/v1/certificates/{cert_id}", json={})

        assert response.status_code == 400
        assert "No fields to update" in response.json()["detail"]


class TestCertificatesViewCount:
    """Test suite for certificate view count feature."""

    def test_view_count_increments_on_detail_view(
        self, client: TestClient, test_supabase_client: Client, clean_test_certificates
    ):
        """Test that view count increments when viewing certificate details.

        Given: A certificate exists with view_count = 0
        When: GET /api/v1/certificates/{id} is called
        Then: view_count should increment by 1
        """
        # Create a test certificate with view_count = 0
        test_cert = {
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "테스트",
            "title": "조회수테스트자격증",
            "raw_id": "TEST_view_count_test",
            "view_count": 0,
        }

        insert_result = (
            test_supabase_client.table("certificates").insert(test_cert).execute()
        )
        cert_id = insert_result.data[0]["id"]

        # First view - should increment from 0 to 1
        response = client.get(f"/api/v1/certificates/{cert_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["view_count"] == 1

        # Second view - should increment from 1 to 2
        response = client.get(f"/api/v1/certificates/{cert_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["view_count"] == 2

    def test_view_count_increments_on_raw_id_view(
        self, client: TestClient, test_supabase_client: Client, clean_test_certificates
    ):
        """Test that view count increments when viewing by raw_id.

        Given: A certificate exists with view_count = 0
        When: GET /api/v1/certificates/raw/{raw_id} is called
        Then: view_count should increment by 1
        """
        # Create a test certificate
        test_cert = {
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "테스트",
            "title": "조회수테스트자격증2",
            "raw_id": "TEST_view_count_raw_id",
            "view_count": 0,
        }

        insert_result = (
            test_supabase_client.table("certificates").insert(test_cert).execute()
        )
        raw_id = insert_result.data[0]["raw_id"]

        # View by raw_id - should increment
        response = client.get(f"/api/v1/certificates/raw/{raw_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["view_count"] == 1

    def test_search_does_not_increment_view_count(
        self, client: TestClient, test_supabase_client: Client, clean_test_certificates
    ):
        """Test that search does NOT increment view count.

        Given: A certificate exists with view_count = 0
        When: GET /api/v1/certificates/search?q={title} is called
        Then: view_count should remain 0 (only detail view increments)
        """
        # Create a test certificate
        test_cert = {
            "categories": [{"code": "T", "name": "국가기술자격"}],
            "series": "테스트",
            "title": "검색조회수테스트",
            "raw_id": "TEST_search_view_count",
            "view_count": 0,
        }

        insert_result = (
            test_supabase_client.table("certificates").insert(test_cert).execute()
        )
        cert_id = insert_result.data[0]["id"]

        # Search for the certificate (should NOT increment view_count)
        response = client.get("/api/v1/certificates/search?q=검색조회수테스트")
        assert response.status_code == 200

        # Check view_count in database directly
        cert = (
            test_supabase_client.table("certificates")
            .select("view_count")
            .eq("id", cert_id)
            .execute()
        )
        assert cert.data[0]["view_count"] == 0
