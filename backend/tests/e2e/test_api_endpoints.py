"""E2E tests for API endpoints using real HTTP requests.

These tests verify the API behavior by making actual HTTP requests
to a running server, similar to how Playwright tests work.
"""

import os

import pytest
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API base URL from environment or use default
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Get CORS origins from environment (첫 번째 origin 사용)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5100")
CORS_TEST_ORIGIN = CORS_ORIGINS.split(",")[0].strip()


@pytest.fixture(scope="module")
def api_url():
    """Get API base URL for testing."""
    return API_BASE_URL


@pytest.fixture(scope="module")
def check_server_running(api_url):
    """Check if the API server is running before running tests."""
    try:
        response = requests.get(f"{api_url}/health", timeout=5)
        if response.status_code != 200:
            pytest.skip(f"API server is not healthy at {api_url}")
    except requests.exceptions.ConnectionError:
        pytest.skip(
            f"API server is not running at {api_url}. Please start the server first."
        )


class TestAPIHealth:
    """E2E tests for health and basic endpoints."""

    def test_health_endpoint(self, api_url, check_server_running):
        """Test that the health endpoint returns 200.

        Given: API server is running
        When: GET /health is called
        Then: Returns 200 with healthy status
        """
        response = requests.get(f"{api_url}/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "service" in data
        print(f"\n[PASS] Health Check: {data}")

    def test_root_endpoint(self, api_url, check_server_running):
        """Test that the root endpoint returns API information.

        Given: API server is running
        When: GET / is called
        Then: Returns 200 with API info
        """
        response = requests.get(f"{api_url}/")

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "version" in data
        print(f"\n[PASS] Root: {data}")


class TestCertificatesAPIE2E:
    """E2E tests for Certificates API endpoints."""

    def test_search_certificates_e2e(self, api_url, check_server_running):
        """Test searching certificates via real HTTP request.

        Given: API server is running with data
        When: GET /api/v1/certificates/search is called
        Then: Returns a list of certificates
        """
        response = requests.get(f"{api_url}/api/v1/certificates/search")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

        print(f"\n[PASS] Search returned {data['total']} certificates")
        if data["items"]:
            print(f"   First certificate: {data['items'][0]['title']}")

    def test_search_with_keyword_e2e(self, api_url, check_server_running):
        """Test searching certificates with keyword.

        Given: API server is running
        When: GET /api/v1/certificates/search?q=정보처리 is called
        Then: Returns matching certificates
        """
        response = requests.get(
            f"{api_url}/api/v1/certificates/search", params={"q": "정보처리"}
        )

        assert response.status_code == 200
        data = response.json()

        print(f"\n[PASS] Keyword search returned {len(data['items'])} results")

    def test_get_categories_e2e(self, api_url, check_server_running):
        """Test getting certificate categories.

        Given: API server is running
        When: GET /api/v1/certificates/categories is called
        Then: Returns a list of categories
        """
        response = requests.get(f"{api_url}/api/v1/certificates/categories")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        print(f"\n[PASS] Found {len(data)} categories")
        if data:
            print(f"   Categories: {', '.join(data[:3])}...")

    def test_pagination_e2e(self, api_url, check_server_running):
        """Test pagination parameters.

        Given: API server is running
        When: GET /api/v1/certificates/search with pagination params
        Then: Returns correct page size
        """
        response = requests.get(
            f"{api_url}/api/v1/certificates/search", params={"page": 1, "page_size": 5}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["page_size"] == 5
        assert len(data["items"]) <= 5

        print(f"\n[PASS] Pagination: Page {data['page']}, Size {data['page_size']}")


class TestAPIErrorHandling:
    """E2E tests for API error handling."""

    def test_404_not_found(self, api_url, check_server_running):
        """Test 404 error handling.

        Given: API server is running
        When: GET /api/v1/certificates/{invalid_id} is called
        Then: Returns 404
        """
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        response = requests.get(f"{api_url}/api/v1/certificates/{fake_uuid}")

        assert response.status_code == 404
        data = response.json()

        assert "detail" in data
        print(f"\n[PASS] 404 Error handled: {data['detail']}")

    def test_cors_headers(self, api_url, check_server_running):
        """Test CORS headers are present.

        Given: API server is running
        When: Cross-origin request is made
        Then: CORS headers are present
        """
        # Make a cross-origin request by adding Origin header (from .env)
        headers = {"Origin": CORS_TEST_ORIGIN}
        response = requests.get(f"{api_url}/health", headers=headers)

        # Check for CORS headers
        assert "access-control-allow-origin" in response.headers
        assert response.headers["access-control-allow-origin"] in [
            "*",
            CORS_TEST_ORIGIN,
        ]
        print(
            f"\n[PASS] CORS headers present: {response.headers.get('access-control-allow-origin')}"
        )


@pytest.mark.parametrize(
    "endpoint",
    [
        "/health",
        "/",
        "/api/v1/certificates/search",
        "/api/v1/certificates/categories",
    ],
)
def test_all_endpoints_accessible(api_url, check_server_running, endpoint):
    """Test that all main endpoints are accessible.

    Given: API server is running
    When: Each endpoint is called
    Then: Returns 200 OK
    """
    response = requests.get(f"{api_url}{endpoint}")

    assert response.status_code == 200
    print(f"\n[PASS] {endpoint}: OK")
