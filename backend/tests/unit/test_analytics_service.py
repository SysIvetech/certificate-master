"""Unit tests for AnalyticsService.

복합 진행도 계산, 이탈 위험 감지 등의 비즈니스 로직을 테스트합니다.
"""

from datetime import date, timedelta

from app.schemas.analytics import (
    LearnerStatus,
    RiskSignalType,
)


class TestCompletionRate:
    """진도율 계산 테스트."""

    def test_calculate_completion_rate_all_completed(self):
        """테스트: 모든 마일스톤 완료 시 100% 반환"""
        # Given: 5개 마일스톤 모두 완료
        milestones = [
            {"week": 1, "title": "Week 1", "completed": True},
            {"week": 2, "title": "Week 2", "completed": True},
            {"week": 3, "title": "Week 3", "completed": True},
            {"week": 4, "title": "Week 4", "completed": True},
            {"week": 5, "title": "Week 5", "completed": True},
        ]

        # When: 진도율 계산
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        completion_rate = service.calculate_completion_rate(milestones)

        # Then: 100.0 반환
        assert completion_rate == 100.0

    def test_calculate_completion_rate_partial(self):
        """테스트: 일부 마일스톤 완료 시 정확한 비율 반환"""
        # Given: 5개 중 3개 완료
        milestones = [
            {"week": 1, "completed": True},
            {"week": 2, "completed": True},
            {"week": 3, "completed": True},
            {"week": 4, "completed": False},
            {"week": 5, "completed": False},
        ]

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        completion_rate = service.calculate_completion_rate(milestones)

        # Then: 60.0 반환
        assert completion_rate == 60.0

    def test_calculate_completion_rate_empty(self):
        """테스트: 마일스톤 없을 시 0% 반환"""
        # Given: 빈 마일스톤 리스트
        milestones = []

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        completion_rate = service.calculate_completion_rate(milestones)

        # Then: 0.0 반환
        assert completion_rate == 0.0


class TestTimeAdherenceRate:
    """시간 이행률 계산 테스트."""

    def test_calculate_time_adherence_exact_match(self):
        """테스트: 계획 시간과 실제 시간이 일치하면 100% 반환"""
        # Given: 계획 10시간, 실제 10시간
        planned_hours = 10.0
        actual_hours = 10.0

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        adherence = service.calculate_time_adherence_rate(planned_hours, actual_hours)

        # Then: 100.0
        assert adherence == 100.0

    def test_calculate_time_adherence_exceeded(self):
        """테스트: 계획보다 많이 공부하면 100% 초과"""
        # Given: 계획 10시간, 실제 15시간
        planned_hours = 10.0
        actual_hours = 15.0

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        adherence = service.calculate_time_adherence_rate(planned_hours, actual_hours)

        # Then: 150.0
        assert adherence == 150.0

    def test_calculate_time_adherence_zero_planned(self):
        """테스트: 계획 시간이 0이면 0% 반환"""
        # Given: 계획 0시간
        planned_hours = 0.0
        actual_hours = 5.0

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        adherence = service.calculate_time_adherence_rate(planned_hours, actual_hours)

        # Then: 0.0
        assert adherence == 0.0


class TestScheduleAdherenceRate:
    """일정 준수율 계산 테스트."""

    def test_calculate_schedule_adherence_on_track(self):
        """테스트: 예상 진도와 실제 진도가 일치하면 100% 반환"""
        # Given: 목표일까지 50일, 경과 25일, 진도 50%
        target_date = date.today() + timedelta(days=25)
        start_date = date.today() - timedelta(days=25)
        current_progress = 50.0

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        adherence = service.calculate_schedule_adherence_rate(
            start_date, target_date, current_progress
        )

        # Then: 100.0 (예상 50%, 실제 50%)
        assert abs(adherence - 100.0) < 0.1

    def test_calculate_schedule_adherence_ahead(self):
        """테스트: 예상보다 앞서면 100% 초과"""
        # Given: 목표일까지 60일, 경과 20일, 진도 50%
        target_date = date.today() + timedelta(days=60)
        start_date = date.today() - timedelta(days=20)
        current_progress = 50.0  # 예상: 25%, 실제: 50%

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        adherence = service.calculate_schedule_adherence_rate(
            start_date, target_date, current_progress
        )

        # Then: > 150%
        assert adherence > 150.0


class TestRiskDetection:
    """이탈 위험 감지 테스트."""

    def test_detect_risk_streak_broken(self):
        """테스트: 7일 이상 체크인 없으면 연속성 단절 신호"""
        # Given: 마지막 체크인이 8일 전
        last_checkin_date = date.today() - timedelta(days=8)

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        risk_signals = service.detect_streak_broken(last_checkin_date)

        # Then: RiskSignal 반환
        assert len(risk_signals) == 1
        assert risk_signals[0].type == RiskSignalType.STREAK_BROKEN
        assert risk_signals[0].severity == "high"

    def test_detect_risk_time_decreased(self):
        """테스트: 최근 7일 평균이 계획의 50% 미만이면 위험"""
        # Given: 계획 3시간/일, 최근 평균 1시간/일
        daily_planned_hours = 3.0
        recent_avg_hours = 1.0

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        risk_signals = service.detect_time_decreased(
            daily_planned_hours, recent_avg_hours
        )

        # Then
        assert len(risk_signals) == 1
        assert risk_signals[0].type == RiskSignalType.TIME_DECREASED
        assert risk_signals[0].severity in ["medium", "high"]

    def test_detect_risk_mood_deteriorated(self):
        """테스트: 연속 3회 tired/stressed면 번아웃 징후"""
        # Given: 최근 기분이 ["stressed", "tired", "stressed"]
        recent_moods = ["stressed", "tired", "stressed"]

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        risk_signals = service.detect_mood_deteriorated(recent_moods)

        # Then
        assert len(risk_signals) == 1
        assert risk_signals[0].type == RiskSignalType.MOOD_DETERIORATED
        assert "번아웃" in risk_signals[0].description


class TestLearnerStatusClassification:
    """학습자 상태 분류 테스트."""

    def test_classify_status_exceeding(self):
        """테스트: 일정 준수율 > 120%면 초과 달성"""
        # Given
        schedule_adherence = 130.0

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        status = service.classify_learner_status(schedule_adherence, current_streak=5)

        # Then
        assert status == LearnerStatus.EXCEEDING

    def test_classify_status_on_track(self):
        """테스트: 80% ≤ 일정 준수율 ≤ 120%면 정상"""
        # Given
        schedule_adherence = 95.0

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        status = service.classify_learner_status(schedule_adherence, current_streak=3)

        # Then
        assert status == LearnerStatus.ON_TRACK

    def test_classify_status_needs_attention(self):
        """테스트: 50% ≤ 일정 준수율 < 80%면 주의 필요"""
        # Given
        schedule_adherence = 65.0

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        status = service.classify_learner_status(schedule_adherence, current_streak=1)

        # Then
        assert status == LearnerStatus.NEEDS_ATTENTION

    def test_classify_status_at_risk(self):
        """테스트: 일정 준수율 < 50% 또는 연속성 = 0이면 이탈 위험"""
        # Given
        schedule_adherence = 30.0

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        status = service.classify_learner_status(schedule_adherence, current_streak=0)

        # Then
        assert status == LearnerStatus.AT_RISK


class TestPredictCompletionDate:
    """완료일 예측 테스트."""

    def test_predict_completion_date_on_schedule(self):
        """테스트: 현재 페이스 유지 시 목표일과 일치"""
        # Given: 목표일까지 30일, 현재 진도 50%, 최근 평균 진도 1.67%/일
        target_date = date.today() + timedelta(days=30)
        current_progress = 50.0
        recent_daily_progress = 1.67  # 30일 후 100% 도달

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        predicted_date = service.predict_completion_date(
            target_date, current_progress, recent_daily_progress
        )

        # Then: 목표일과 거의 일치
        assert abs((predicted_date - target_date).days) < 2

    def test_predict_completion_date_ahead(self):
        """테스트: 빠른 페이스면 목표일보다 빠름"""
        # Given: 목표일까지 30일, 현재 진도 50%, 최근 평균 진도 3%/일
        target_date = date.today() + timedelta(days=30)
        current_progress = 50.0
        recent_daily_progress = 3.0  # 빠른 페이스

        # When
        from app.services.analytics_service import AnalyticsService

        service = AnalyticsService()
        predicted_date = service.predict_completion_date(
            target_date, current_progress, recent_daily_progress
        )

        # Then: 목표일보다 빠름
        assert predicted_date < target_date
