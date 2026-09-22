"""Integration tests for health check endpoint.

Simple tests to verify the API is running correctly.
"""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    """Test the health check endpoint.

    Given: The API is running
    When: GET /health is called
    Then: It should return 200 with status "healthy"
    """
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "certificate-master-api"
    assert "environment" in data


def test_root_endpoint(client: TestClient):
    """Test the root endpoint.

    Given: The API is running
    When: GET / is called
    Then: It should return API information
    """
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()

    assert "name" in data
    assert "version" in data
    assert "docs" in data
