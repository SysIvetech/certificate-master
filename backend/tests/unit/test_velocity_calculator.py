"""
Unit tests for VelocityCalculator service.
Following TDD: RED → GREEN → VERIFY
"""

from datetime import date, datetime

import pytest

from app.services.velocity_calculator import VelocityCalculator


class TestVelocityCalculator:
    """Test suite for velocity and progress prediction calculations."""

    @pytest.fixture
    def sample_study_plan(self):
        """Sample study plan for testing."""
        return {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "created_at": datetime(2026, 1, 1),
            "target_date": "2026-04-01",  # 90 days from start
            "daily_study_hours": 2.0,
            "milestones": [
                {"week": 1, "title": "Week 1", "completed": True},
                {"week": 2, "title": "Week 2", "completed": True},
                {"week": 3, "title": "Week 3", "completed": True},
                {"week": 4, "title": "Week 4", "completed": False},
                {"week": 5, "title": "Week 5", "completed": False},
            ],
            "progress_percentage": 60.0,
        }

    @pytest.fixture
    def sample_snapshots(self):
        """Sample progress snapshots for testing."""
        return [
            {
                "snapshot_date": date(2026, 1, 30),
                "progress_percentage": 60.0,
                "milestones_completed": 3,
            },
            {
                "snapshot_date": date(2026, 1, 20),
                "progress_percentage": 40.0,
                "milestones_completed": 2,
            },
            {
                "snapshot_date": date(2026, 1, 10),
                "progress_percentage": 20.0,
                "milestones_completed": 1,
            },
        ]

    def test_calculate_expected_progress_linear(self, sample_study_plan):
        """
        RED → GREEN → VERIFY
        Test expected progress calculation based on linear timeline.
        """
        calculator = VelocityCalculator(sample_study_plan, [])

        # On day 30 of 90-day plan, expected progress should be ~33.3%
        current_date = date(2026, 1, 30)
        expected = calculator.calculate_expected_progress(current_date)

        assert abs(expected - 32.2) < 1.0  # Allow 1% tolerance

    def test_calculate_expected_progress_midpoint(self, sample_study_plan):
        """
        RED → GREEN → VERIFY
        Test expected progress at midpoint of plan.
        """
        calculator = VelocityCalculator(sample_study_plan, [])

        # Day 45 of 90-day plan should be 50%
        current_date = date(2026, 2, 15)
        expected = calculator.calculate_expected_progress(current_date)

        assert abs(expected - 50.0) < 1.0

    def test_calculate_actual_progress_from_milestones(self, sample_study_plan):
        """
        RED → GREEN → VERIFY
        Test actual progress calculation from milestone completion.
        """
        calculator = VelocityCalculator(sample_study_plan, [])

        actual = calculator.calculate_actual_progress()

        # 3 of 5 milestones completed = 60%
        assert abs(actual - 60.0) < 0.1

    def test_calculate_velocity_from_snapshots(
        self, sample_study_plan, sample_snapshots
    ):
        """
        RED → GREEN → VERIFY
        Test velocity calculation (progress per day).
        """
        calculator = VelocityCalculator(sample_study_plan, sample_snapshots)

        velocity = calculator.calculate_velocity()

        # 40% progress over 20 days = 2% per day
        assert abs(velocity - 2.0) < 0.1

    def test_calculate_velocity_no_snapshots(self, sample_study_plan):
        """
        RED → GREEN → VERIFY
        Test velocity returns 0 when no snapshot data.
        """
        calculator = VelocityCalculator(sample_study_plan, [])

        velocity = calculator.calculate_velocity()

        assert velocity == 0.0

    def test_predict_completion_date_on_track(
        self, sample_study_plan, sample_snapshots
    ):
        """
        RED → GREEN → VERIFY
        Test completion date prediction when on track.
        """
        calculator = VelocityCalculator(sample_study_plan, sample_snapshots)

        predicted = calculator.predict_completion_date()

        # At 2% velocity, 40% remaining = 20 days from Jan 30 = Feb 19
        expected_date = date(2026, 2, 19)
        assert abs((predicted - expected_date).days) <= 2  # Allow 2-day tolerance

    def test_predict_completion_date_zero_velocity(self, sample_study_plan):
        """
        RED → GREEN → VERIFY
        Test prediction defaults to target date when velocity is zero.
        """
        calculator = VelocityCalculator(sample_study_plan, [])

        predicted = calculator.predict_completion_date()

        assert (
            predicted == datetime.fromisoformat(sample_study_plan["target_date"]).date()
        )

    def test_velocity_status_ahead(self, sample_study_plan, sample_snapshots):
        """
        RED → GREEN → VERIFY
        Test status classification: ahead of schedule.
        """
        calculator = VelocityCalculator(sample_study_plan, sample_snapshots)

        # Mock current date to make actual > expected
        calculator.calculate_expected_progress = lambda cd=None: 30.0  # Expected 30%
        calculator.calculate_actual_progress = lambda: 60.0  # Actual 60%

        status = calculator.get_velocity_status()

        assert status["status"] == "ahead"
        assert status["progress_delta"] > 10

    def test_velocity_status_on_track(self, sample_study_plan, sample_snapshots):
        """
        RED → GREEN → VERIFY
        Test status classification: on track.
        """
        calculator = VelocityCalculator(sample_study_plan, sample_snapshots)

        calculator.calculate_expected_progress = lambda cd=None: 58.0
        calculator.calculate_actual_progress = lambda: 60.0

        status = calculator.get_velocity_status()

        assert status["status"] == "on-track"
        assert -5 < status["progress_delta"] <= 10

    def test_velocity_status_behind(self, sample_study_plan, sample_snapshots):
        """
        RED → GREEN → VERIFY
        Test status classification: behind schedule.
        """
        calculator = VelocityCalculator(sample_study_plan, sample_snapshots)

        calculator.calculate_expected_progress = lambda cd=None: 70.0
        calculator.calculate_actual_progress = lambda: 60.0

        status = calculator.get_velocity_status()

        assert status["status"] == "behind"
        assert -15 < status["progress_delta"] <= -5

    def test_velocity_status_critical(self, sample_study_plan, sample_snapshots):
        """
        RED → GREEN → VERIFY
        Test status classification: critically behind.
        """
        calculator = VelocityCalculator(sample_study_plan, sample_snapshots)

        calculator.calculate_expected_progress = lambda cd=None: 80.0
        calculator.calculate_actual_progress = lambda: 60.0

        status = calculator.get_velocity_status()

        assert status["status"] == "critical"
        assert status["progress_delta"] <= -15

    def test_velocity_status_response_structure(
        self, sample_study_plan, sample_snapshots
    ):
        """
        RED → GREEN → VERIFY
        Test that velocity status returns complete response structure.
        """
        calculator = VelocityCalculator(sample_study_plan, sample_snapshots)

        status = calculator.get_velocity_status()

        # Verify all required fields present
        assert "expected_progress" in status
        assert "actual_progress" in status
        assert "progress_delta" in status
        assert "velocity" in status
        assert "predicted_date" in status
        assert "status" in status

        # Verify types
        assert isinstance(status["expected_progress"], (int, float))
        assert isinstance(status["actual_progress"], (int, float))
        assert isinstance(status["progress_delta"], (int, float))
        assert isinstance(status["velocity"], (int, float))
        assert isinstance(status["predicted_date"], str)
        assert status["status"] in ["ahead", "on-track", "behind", "critical"]

    def test_velocity_calculation_edge_case_same_day(self, sample_study_plan):
        """
        RED → GREEN → VERIFY
        Test velocity calculation when all snapshots are same day.
        """
        same_day_snapshots = [
            {
                "snapshot_date": date(2026, 1, 15),
                "progress_percentage": 30.0,
            },
            {
                "snapshot_date": date(2026, 1, 15),
                "progress_percentage": 30.0,
            },
        ]

        calculator = VelocityCalculator(sample_study_plan, same_day_snapshots)
        velocity = calculator.calculate_velocity()

        # Should handle division by zero gracefully
        assert velocity == 0.0

    def test_predicted_date_format(self, sample_study_plan, sample_snapshots):
        """
        RED → GREEN → VERIFY
        Test predicted date is in ISO format.
        """
        calculator = VelocityCalculator(sample_study_plan, sample_snapshots)
        status = calculator.get_velocity_status()

        # Should be ISO date string
        predicted_date = status["predicted_date"]
        assert len(predicted_date) == 10  # YYYY-MM-DD
        assert predicted_date[4] == "-"
        assert predicted_date[7] == "-"

        # Should be parseable
        datetime.fromisoformat(predicted_date)

    def test_progress_rounding(self, sample_study_plan, sample_snapshots):
        """
        RED → GREEN → VERIFY
        Test that progress values are properly rounded.
        """
        calculator = VelocityCalculator(sample_study_plan, sample_snapshots)
        status = calculator.get_velocity_status()

        # All progress values should be rounded to 1 decimal
        assert (
            abs(status["expected_progress"] - round(status["expected_progress"], 1))
            < 0.01
        )
        assert (
            abs(status["actual_progress"] - round(status["actual_progress"], 1)) < 0.01
        )
        assert abs(status["progress_delta"] - round(status["progress_delta"], 1)) < 0.01

    def test_velocity_rounding(self, sample_study_plan, sample_snapshots):
        """
        RED → GREEN → VERIFY
        Test that velocity is properly rounded to 2 decimals.
        """
        calculator = VelocityCalculator(sample_study_plan, sample_snapshots)
        status = calculator.get_velocity_status()

        # Velocity should be rounded to 2 decimals
        assert abs(status["velocity"] - round(status["velocity"], 2)) < 0.001
