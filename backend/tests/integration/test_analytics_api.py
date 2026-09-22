"""Integration tests for Analytics API endpoints.

Tests progress analytics, learning patterns, and risk detection.
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(authenticated_client):
    """FastAPI test client with authentication.

    Uses the authenticated_client fixture from conftest which
    overrides the authentication dependency with a mock user.
    """
    return authenticated_client


@pytest.fixture
def test_certificate_id():
    """Return a valid certificate ID for testing.

    Note: This should be a real certificate ID from your Supabase database.
    """
    # TODO: Replace with actual certificate ID from test database
    return "test-cert-uuid-123"


@pytest.fixture
def test_study_plan(client, auth_headers, test_certificate_id):
    """Create a test study plan for analytics tests.

    Returns:
        dict: Created study plan with id, milestones, etc.
    """
    target_date = (date.today() + timedelta(days=90)).isoformat()
    payload = {
        "certificate_id": test_certificate_id,
        "target_date": target_date,
        "daily_hours": 3.0,
        "milestones": [
            {
                "week": 1,
                "title": "Week 1: 기초 학습",
                "description": "기본 개념 이해",
                "hours": 21.0,
                "completed": True,
            },
            {
                "week": 2,
                "title": "Week 2: 심화 학습",
                "description": "심화 개념 학습",
                "hours": 21.0,
                "completed": False,
            },
            {
                "week": 3,
                "title": "Week 3: 문제 풀이",
                "description": "실전 문제 풀이",
                "hours": 21.0,
                "completed": False,
            },
        ],
    }

    response = client.post("/api/v1/study-plans/", json=payload, headers=auth_headers)

    if response.status_code != 201:
        pytest.skip(f"Failed to create test study plan: {response.json()}")

    return response.json()


@pytest.fixture
def test_checkins(client, auth_headers, test_study_plan):
    """Create test checkins for the study plan.

    Returns:
        list: Created checkins
    """
    plan_id = test_study_plan["id"]
    checkins = []

    # Create 5 consecutive checkins
    for i in range(5):
        checkin_date = (date.today() - timedelta(days=4 - i)).isoformat()
        payload = {
            "study_plan_id": plan_id,
            "checkin_date": checkin_date,
            "hours_studied": 2.5,
            "notes": f"Day {i+1} study session",
            "mood": "good",
        }

        response = client.post("/api/v1/checkins/", json=payload, headers=auth_headers)

        if response.status_code == 201:
            checkins.append(response.json())

    return checkins


class TestProgressAnalyticsAPI:
    """Test suite for Progress Analytics API endpoints."""

    @pytest.mark.skip(reason="Requires real database with study plan and checkins")
    def test_get_progress_analytics_success(
        self, client, auth_headers, test_study_plan, test_checkins
    ):
        """Test getting progress analytics for a study plan with checkins.

        Given: A study plan with completed milestones and checkins
        When: GET /api/v1/analytics/progress/{study_plan_id} is called
        Then: It should return detailed analytics with all metrics
        """
        # Given
        plan_id = test_study_plan["id"]

        # When
        response = client.get(
            f"/api/v1/analytics/progress/{plan_id}", headers=auth_headers
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["plan_id"] == plan_id

        # Core metrics
        assert "completion_rate" in data
        assert 0.0 <= data["completion_rate"] <= 100.0
        assert data["completion_rate"] > 0  # We have 1 completed milestone

        assert "time_adherence_rate" in data
        assert data["time_adherence_rate"] >= 0.0

        assert "schedule_adherence_rate" in data
        assert data["schedule_adherence_rate"] >= 0.0

        assert "current_streak" in data
        assert data["current_streak"] >= 0

        # Additional metrics
        assert "learning_pattern_score" in data
        assert "review_urgency" in data
        assert data["review_urgency"] in ["low", "medium", "high"]

        # Status and predictions
        assert "status" in data
        assert data["status"] in ["exceeding", "on_track", "needs_attention", "at_risk"]

        assert "predicted_completion_date" in data

        # Recommendations and risk signals
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

        assert "risk_signals" in data
        assert isinstance(data["risk_signals"], list)

    def test_get_progress_analytics_without_checkins(
        self, client, auth_headers, test_study_plan
    ):
        """Test getting progress analytics for a study plan without checkins.

        Given: A study plan without any checkins
        When: GET /api/v1/analytics/progress/{study_plan_id} is called
        Then: It should return analytics with default values
        """
        # Given
        plan_id = test_study_plan["id"]

        # When
        response = client.get(
            f"/api/v1/analytics/progress/{plan_id}", headers=auth_headers
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        assert data["plan_id"] == plan_id
        assert data["current_streak"] == 0  # No checkins
        assert data["completion_rate"] >= 0.0

    def test_get_progress_analytics_without_auth(self):
        """Test getting progress analytics without authentication.

        Given: No authentication headers
        When: GET /api/v1/analytics/progress/{study_plan_id} is called
        Then: It should return 401 Unauthorized
        """
        # Given - use a client without auth override

        unauthenticated_client = TestClient(app)
        plan_id = "test-plan-id"

        # When
        response = unauthenticated_client.get(f"/api/v1/analytics/progress/{plan_id}")

        # Then
        assert response.status_code == 401

    def test_get_progress_analytics_not_found(self, client):
        """Test getting progress analytics for non-existent study plan.

        Given: A non-existent study plan ID
        When: GET /api/v1/analytics/progress/{study_plan_id} is called
        Then: It should return 404 Not Found
        """
        # Given
        non_existent_id = "00000000-0000-0000-0000-000000000000"

        # When
        response = client.get(f"/api/v1/analytics/progress/{non_existent_id}")

        # Then
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_progress_analytics_other_user_plan(
        self, client, auth_headers, test_study_plan
    ):
        """Test accessing another user's study plan analytics.

        Given: A study plan owned by another user
        When: GET /api/v1/analytics/progress/{study_plan_id} is called with different user token
        Then: It should return 404 Not Found (due to user_id filter)
        """
        # Given
        plan_id = test_study_plan["id"]
        other_user_headers = {"Authorization": "Bearer other_user_token"}

        # When
        response = client.get(
            f"/api/v1/analytics/progress/{plan_id}", headers=other_user_headers
        )

        # Then
        assert response.status_code in [401, 404]

    def test_progress_analytics_completion_rate_calculation(
        self, client, auth_headers, test_study_plan
    ):
        """Test that completion rate is calculated correctly.

        Given: A study plan with 1 out of 3 milestones completed
        When: GET /api/v1/analytics/progress/{study_plan_id} is called
        Then: completion_rate should be approximately 33.33%
        """
        # Given
        plan_id = test_study_plan["id"]

        # When
        response = client.get(
            f"/api/v1/analytics/progress/{plan_id}", headers=auth_headers
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        # 1 out of 3 milestones completed = 33.33%
        assert 30.0 <= data["completion_rate"] <= 35.0

    def test_progress_analytics_risk_signals_streak_broken(
        self, client, auth_headers, test_study_plan
    ):
        """Test risk signal detection for broken streak.

        Given: A study plan with last checkin more than 7 days ago
        When: GET /api/v1/analytics/progress/{study_plan_id} is called
        Then: It should include a 'streak_broken' risk signal
        """
        # Given
        plan_id = test_study_plan["id"]

        # Create an old checkin (10 days ago)
        old_checkin_date = (date.today() - timedelta(days=10)).isoformat()
        checkin_payload = {
            "study_plan_id": plan_id,
            "checkin_date": old_checkin_date,
            "hours_studied": 2.0,
            "notes": "Old study session",
            "mood": "good",
        }

        client.post("/api/v1/checkins/", json=checkin_payload, headers=auth_headers)

        # When
        response = client.get(
            f"/api/v1/analytics/progress/{plan_id}", headers=auth_headers
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        # Check for streak_broken risk signal
        risk_signals = data["risk_signals"]
        streak_broken_signals = [
            signal for signal in risk_signals if signal["type"] == "streak_broken"
        ]

        # Should have at least one streak_broken signal
        assert len(streak_broken_signals) >= 1
        assert streak_broken_signals[0]["severity"] == "high"

    def test_progress_analytics_learner_status(
        self, client, auth_headers, test_study_plan, test_checkins
    ):
        """Test learner status classification.

        Given: A study plan with regular checkins
        When: GET /api/v1/analytics/progress/{study_plan_id} is called
        Then: It should classify the learner status correctly
        """
        # Given
        plan_id = test_study_plan["id"]

        # When
        response = client.get(
            f"/api/v1/analytics/progress/{plan_id}", headers=auth_headers
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        # Status should be one of the valid values
        valid_statuses = ["exceeding", "on_track", "needs_attention", "at_risk"]
        assert data["status"] in valid_statuses

    def test_progress_analytics_recommendations(
        self, client, auth_headers, test_study_plan, test_checkins
    ):
        """Test that recommendations are provided.

        Given: A study plan with analytics data
        When: GET /api/v1/analytics/progress/{study_plan_id} is called
        Then: It should provide actionable recommendations
        """
        # Given
        plan_id = test_study_plan["id"]

        # When
        response = client.get(
            f"/api/v1/analytics/progress/{plan_id}", headers=auth_headers
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        # Should have at least one recommendation
        assert len(data["recommendations"]) >= 1

        # Recommendations should be strings
        for recommendation in data["recommendations"]:
            assert isinstance(recommendation, str)
            assert len(recommendation) > 0


class TestLearningPatternAPI:
    """Test suite for Learning Pattern API endpoints.

    Note: These tests will fail until LearningPattern API is implemented.
    """

    @pytest.mark.skip(reason="LearningPattern API not yet implemented")
    def test_get_learning_pattern_success(
        self, client, auth_headers, test_study_plan, test_checkins
    ):
        """Test getting learning pattern analysis for a study plan.

        Given: A study plan with multiple checkins
        When: GET /api/v1/analytics/learning-pattern/{study_plan_id} is called
        Then: It should return learning pattern analysis
        """
        # Given
        plan_id = test_study_plan["id"]

        # When
        response = client.get(
            f"/api/v1/analytics/learning-pattern/{plan_id}", headers=auth_headers
        )

        # Then
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert data["plan_id"] == plan_id

        # Time-based analysis
        assert "preferred_time_slots" in data
        assert isinstance(data["preferred_time_slots"], list)

        assert "average_session_duration" in data
        assert data["average_session_duration"] >= 0.0

        # Weekday efficiency
        assert "best_weekday" in data
        assert "worst_weekday" in data

        # Mood trend
        assert "mood_trend" in data
        assert data["mood_trend"] in ["improving", "stable", "declining"]

        assert "recent_moods" in data
        assert isinstance(data["recent_moods"], list)

        # Consistency
        assert "consistency_score" in data
        assert 0.0 <= data["consistency_score"] <= 100.0

    @pytest.mark.skip(reason="LearningPattern API not yet implemented")
    def test_get_learning_pattern_without_auth(self, client, test_study_plan):
        """Test getting learning pattern without authentication.

        Given: No authentication headers
        When: GET /api/v1/analytics/learning-pattern/{study_plan_id} is called
        Then: It should return 401 Unauthorized
        """
        # Given
        plan_id = test_study_plan["id"]

        # When
        response = client.get(f"/api/v1/analytics/learning-pattern/{plan_id}")

        # Then
        assert response.status_code == 401

    @pytest.mark.skip(reason="LearningPattern API not yet implemented")
    def test_get_learning_pattern_not_found(self, client, auth_headers):
        """Test getting learning pattern for non-existent study plan.

        Given: A non-existent study plan ID
        When: GET /api/v1/analytics/learning-pattern/{study_plan_id} is called
        Then: It should return 404 Not Found
        """
        # Given
        non_existent_id = "00000000-0000-0000-0000-000000000000"

        # When
        response = client.get(
            f"/api/v1/analytics/learning-pattern/{non_existent_id}",
            headers=auth_headers,
        )

        # Then
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.skip(reason="LearningPattern API not yet implemented")
    def test_get_learning_pattern_insufficient_data(
        self, client, auth_headers, test_study_plan
    ):
        """Test getting learning pattern with insufficient checkins.

        Given: A study plan with fewer than 3 checkins
        When: GET /api/v1/analytics/learning-pattern/{study_plan_id} is called
        Then: It should return limited pattern data or a specific message
        """
        # Given
        plan_id = test_study_plan["id"]

        # Create only 2 checkins
        for i in range(2):
            checkin_date = (date.today() - timedelta(days=1 - i)).isoformat()
            payload = {
                "study_plan_id": plan_id,
                "checkin_date": checkin_date,
                "hours_studied": 2.0,
                "notes": f"Study session {i+1}",
                "mood": "good",
            }

            client.post("/api/v1/checkins/", json=payload, headers=auth_headers)

        # When
        response = client.get(
            f"/api/v1/analytics/learning-pattern/{plan_id}", headers=auth_headers
        )

        # Then
        # Should either return 200 with limited data or 400 with a message
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.json()
            # Check that it indicates insufficient data
            assert data.get("consistency_score", 0.0) >= 0.0
