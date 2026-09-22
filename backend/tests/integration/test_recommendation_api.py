"""Integration tests for Recommendation API.

RED phase - Tests for POST /api/v1/recommendations/ endpoint.
"""


class TestRecommendationAPI:
    """Test recommendation API endpoint."""

    def test_recommendations_endpoint_exists(self, client):
        """Test that recommendations endpoint exists and accepts POST requests."""
        # POST request should return 200 (no auth required for recommendations)
        response = client.post(
            "/api/v1/recommendations/",
            json={
                "purpose": "취업",
                "interest_domains": ["IT개발", "데이터"],
                "study_timeline": "6개월 이하",
                "difficulty_preference": "중간",
                "user_summary": "데이터 분석 이직을 준비 중입니다.",
            },
        )
        # Should NOT return 404 (endpoint should exist)
        assert response.status_code != 404

    def test_recommendations_invalid_interest_domain(self, client):
        """Test recommendations with invalid interest_domains."""
        response = client.post(
            "/api/v1/recommendations/",
            json={
                "purpose": "취업",
                "interest_domains": ["잘못된 구분"],
                "study_timeline": "6개월 이하",
                "difficulty_preference": "중간",
                "user_summary": "데이터 분석 이직을 준비 중입니다.",
            },
        )
        # Should get 422 (validation error)
        assert response.status_code == 422

    def test_recommendations_invalid_timeline(self, client):
        """Test recommendations with invalid study_timeline."""
        response = client.post(
            "/api/v1/recommendations/",
            json={
                "purpose": "취업",
                "interest_domains": ["IT개발"],
                "study_timeline": "1주 이내",
                "difficulty_preference": "중간",
                "user_summary": "데이터 분석 이직을 준비 중입니다.",
            },
        )
        # Should get 422 (validation error)
        assert response.status_code == 422
