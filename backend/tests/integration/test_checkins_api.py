"""Integration tests for Checkins API endpoints.

Tests all CRUD operations for checkins with authentication.
MariaDB (SQLAlchemy) 기반으로 마이그레이션됨.
"""

from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.models.certificate import Certificate as CertificateModel
from app.models.study_plan import StudyPlan as StudyPlanModel


@pytest.fixture
def test_study_plan_id(test_db_session):
    """Return a valid study plan ID from the database for testing."""
    # First check if there's an existing study plan
    plan = test_db_session.query(StudyPlanModel).first()
    if plan:
        return plan.id

    # If no study plan, create one
    cert = test_db_session.query(CertificateModel).first()
    if not cert:
        pytest.skip("No certificates in database to test with")

    # Create a test study plan
    import uuid

    plan_id = str(uuid.uuid4())
    plan = StudyPlanModel(
        id=plan_id,
        user_id="mock-user-id-00000000",
        certificate_id=cert.id,
        title="Test Study Plan",
        target_date=date.today() + timedelta(days=90),
        daily_study_hours=2.0,
        milestones=[
            {
                "week": 1,
                "title": "Week 1",
                "description": "Basic",
                "hours": 10.0,
                "completed": False,
            }
        ],
    )
    test_db_session.add(plan)
    test_db_session.commit()

    return plan_id


class TestCheckinsAPI:
    """Test suite for Checkins API endpoints."""

    def test_create_checkin(self, authenticated_client, test_study_plan_id):
        """Test creating a new checkin."""
        # Given - use unique date (200 days ago)
        checkin_date = (date.today() - timedelta(days=200)).isoformat()
        payload = {
            "study_plan_id": test_study_plan_id,
            "checkin_date": checkin_date,
            "hours_studied": 2.5,
            "notes": "오늘 열심히 공부했습니다.",
            "mood": "good",
        }

        # When
        response = authenticated_client.post("/api/v1/checkins/", json=payload)

        # Then
        assert response.status_code == 201
        data = response.json()
        assert data["study_plan_id"] == test_study_plan_id
        assert data["hours_studied"] == 2.5
        assert data["mood"] == "good"
        assert "id" in data
        assert "created_at" in data

    def test_create_checkin_without_auth(self, client, test_study_plan_id):
        """Test creating checkin without authentication.

        Note: 현재 인증이 비활성화되어 있어서 (MockUser),
        인증 없이도 요청이 성공합니다. 인증 구현 후 수정 필요.
        """
        # Given - use unique date (201 days ago)
        checkin_date = (date.today() - timedelta(days=201)).isoformat()
        payload = {
            "study_plan_id": test_study_plan_id,
            "checkin_date": checkin_date,
            "hours_studied": 1.5,
            "mood": "okay",
        }

        # When
        response = client.post("/api/v1/checkins/", json=payload)

        # Then - 현재 인증 비활성화 상태이므로 201 반환
        # 인증 구현 후: assert response.status_code == 401
        assert response.status_code == 201

    def test_create_checkin_invalid_study_plan(self, authenticated_client):
        """Test creating checkin with invalid study plan ID."""
        # Given
        payload = {
            "study_plan_id": str(uuid4()),
            "hours_studied": 2.0,
            "mood": "good",
        }

        # When
        response = authenticated_client.post("/api/v1/checkins/", json=payload)

        # Then
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_my_checkins(self, authenticated_client):
        """Test getting user's checkins."""
        # When
        response = authenticated_client.get("/api/v1/checkins/")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_get_my_checkins_without_auth(self, client):
        """Test getting checkins without authentication.

        Note: 현재 인증이 비활성화되어 있어서 (MockUser),
        인증 없이도 요청이 성공합니다. 인증 구현 후 수정 필요.
        """
        # When
        response = client.get("/api/v1/checkins/")

        # Then - 현재 인증 비활성화 상태이므로 200 반환
        # 인증 구현 후: assert response.status_code == 401
        assert response.status_code == 200

    def test_get_checkin_by_id(self, authenticated_client, test_study_plan_id):
        """Test getting a specific checkin by ID."""
        # Create a checkin first (205 days ago)
        checkin_date = (date.today() - timedelta(days=205)).isoformat()
        payload = {
            "study_plan_id": test_study_plan_id,
            "checkin_date": checkin_date,
            "hours_studied": 3.0,
            "mood": "great",
        }

        create_response = authenticated_client.post("/api/v1/checkins/", json=payload)
        assert create_response.status_code == 201
        checkin_id = create_response.json()["id"]

        # When
        response = authenticated_client.get(f"/api/v1/checkins/{checkin_id}")

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == checkin_id
        assert data["hours_studied"] == 3.0

    def test_get_checkin_not_found(self, authenticated_client):
        """Test getting a non-existent checkin."""
        # When
        fake_id = str(uuid4())
        response = authenticated_client.get(f"/api/v1/checkins/{fake_id}")

        # Then
        assert response.status_code == 404

    def test_update_checkin(self, authenticated_client, test_study_plan_id):
        """Test updating a checkin."""
        # Create a checkin first (210 days ago)
        checkin_date = (date.today() - timedelta(days=210)).isoformat()
        payload = {
            "study_plan_id": test_study_plan_id,
            "checkin_date": checkin_date,
            "hours_studied": 2.0,
            "mood": "okay",
        }

        create_response = authenticated_client.post("/api/v1/checkins/", json=payload)
        assert create_response.status_code == 201
        checkin_id = create_response.json()["id"]

        # When
        update_payload = {"hours_studied": 4.0, "mood": "great"}
        response = authenticated_client.patch(
            f"/api/v1/checkins/{checkin_id}", json=update_payload
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["hours_studied"] == 4.0
        assert data["mood"] == "great"

    def test_update_checkin_no_fields(self, authenticated_client, test_study_plan_id):
        """Test updating a checkin with no fields should fail."""
        # Create a checkin first (215 days ago)
        checkin_date = (date.today() - timedelta(days=215)).isoformat()
        payload = {
            "study_plan_id": test_study_plan_id,
            "checkin_date": checkin_date,
            "hours_studied": 2.0,
            "mood": "good",
        }

        create_response = authenticated_client.post("/api/v1/checkins/", json=payload)
        assert create_response.status_code == 201
        checkin_id = create_response.json()["id"]

        # When
        response = authenticated_client.patch(f"/api/v1/checkins/{checkin_id}", json={})

        # Then
        assert response.status_code == 400

    def test_update_checkin_not_found(self, authenticated_client):
        """Test updating a non-existent checkin."""
        # When
        fake_id = str(uuid4())
        response = authenticated_client.patch(
            f"/api/v1/checkins/{fake_id}", json={"hours_studied": 3.0}
        )

        # Then
        assert response.status_code == 404

    def test_delete_checkin(self, authenticated_client, test_study_plan_id):
        """Test deleting a checkin."""
        # Create a checkin first (220 days ago)
        checkin_date = (date.today() - timedelta(days=220)).isoformat()
        payload = {
            "study_plan_id": test_study_plan_id,
            "checkin_date": checkin_date,
            "hours_studied": 2.0,
            "mood": "good",
        }

        create_response = authenticated_client.post("/api/v1/checkins/", json=payload)
        assert create_response.status_code == 201
        checkin_id = create_response.json()["id"]

        # When
        response = authenticated_client.delete(f"/api/v1/checkins/{checkin_id}")

        # Then
        assert response.status_code == 204

        # Verify deletion
        get_response = authenticated_client.get(f"/api/v1/checkins/{checkin_id}")
        assert get_response.status_code == 404

    def test_delete_checkin_not_found(self, authenticated_client):
        """Test deleting a non-existent checkin."""
        # When
        fake_id = str(uuid4())
        response = authenticated_client.delete(f"/api/v1/checkins/{fake_id}")

        # Then
        assert response.status_code == 404

    def test_get_checkin_stats(self, authenticated_client, test_study_plan_id):
        """Test getting checkin statistics."""
        # Create some checkins first (230+ days ago)
        for i in range(3):
            checkin_date = (date.today() - timedelta(days=230 + i)).isoformat()
            payload = {
                "study_plan_id": test_study_plan_id,
                "checkin_date": checkin_date,
                "hours_studied": 2.0 + i * 0.5,
                "mood": "good",
            }
            authenticated_client.post("/api/v1/checkins/", json=payload)

        # When
        response = authenticated_client.get(
            f"/api/v1/checkins/stats?study_plan_id={test_study_plan_id}"
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "total_hours" in data
        assert "total_days" in data
        assert "average_hours_per_day" in data
        assert "current_streak" in data
        assert "longest_streak" in data

    def test_filter_checkins_by_date_range(
        self, authenticated_client, test_study_plan_id
    ):
        """Test filtering checkins by date range."""
        # Create checkins (240+ days ago)
        for i in range(5):
            checkin_date = (date.today() - timedelta(days=240 + i)).isoformat()
            payload = {
                "study_plan_id": test_study_plan_id,
                "checkin_date": checkin_date,
                "hours_studied": 2.0,
                "mood": "good",
            }
            authenticated_client.post("/api/v1/checkins/", json=payload)

        # When - filter by date range
        start_date = (date.today() - timedelta(days=244)).isoformat()
        end_date = (date.today() - timedelta(days=241)).isoformat()
        response = authenticated_client.get(
            f"/api/v1/checkins/?start_date={start_date}&end_date={end_date}"
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        # Should return checkins within the date range
