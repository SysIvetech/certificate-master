"""Unit tests for LearningPatternService.

학습 패턴 분석 로직을 테스트합니다.
"""

from datetime import datetime, timedelta

from app.services.learning_pattern_service import LearningPatternService


class TestTimeSlotAnalysis:
    """선호 학습 시간대 분석 테스트."""

    def test_analyze_time_slots_morning(self):
        """테스트: 오전에 주로 학습하는 패턴 감지"""
        # Given: 오전 시간대 체크인 3개
        service = LearningPatternService()
        checkins = [
            {"created_at": "2026-01-01T09:00:00Z"},
            {"created_at": "2026-01-02T10:30:00Z"},
            {"created_at": "2026-01-03T08:15:00Z"},
        ]

        # When
        time_slots = service.analyze_time_slots(checkins)

        # Then
        assert "오전" in time_slots

    def test_analyze_time_slots_evening(self):
        """테스트: 저녁에 주로 학습하는 패턴 감지"""
        # Given: 저녁 시간대 체크인 3개
        service = LearningPatternService()
        checkins = [
            {"created_at": "2026-01-01T19:00:00Z"},
            {"created_at": "2026-01-02T20:30:00Z"},
            {"created_at": "2026-01-03T21:15:00Z"},
        ]

        # When
        time_slots = service.analyze_time_slots(checkins)

        # Then
        assert "저녁" in time_slots

    def test_analyze_time_slots_mixed(self):
        """테스트: 혼합 시간대 학습 패턴"""
        # Given: 오전 2회, 저녁 2회
        service = LearningPatternService()
        checkins = [
            {"created_at": "2026-01-01T09:00:00Z"},  # 오전
            {"created_at": "2026-01-02T10:00:00Z"},  # 오전
            {"created_at": "2026-01-03T19:00:00Z"},  # 저녁
            {"created_at": "2026-01-04T20:00:00Z"},  # 저녁
        ]

        # When
        time_slots = service.analyze_time_slots(checkins)

        # Then: 둘 다 포함 (빈도 순)
        assert len(time_slots) == 2
        assert "오전" in time_slots or "저녁" in time_slots

    def test_analyze_time_slots_empty(self):
        """테스트: 체크인 없을 시 빈 리스트 반환"""
        # Given
        service = LearningPatternService()
        checkins = []

        # When
        time_slots = service.analyze_time_slots(checkins)

        # Then
        assert time_slots == []

    def test_analyze_time_slots_insufficient_frequency(self):
        """테스트: 빈도가 낮으면 제외"""
        # Given: 각 시간대 1회씩 (2회 미만)
        service = LearningPatternService()
        checkins = [
            {"created_at": "2026-01-01T09:00:00Z"},  # 오전
            {"created_at": "2026-01-02T13:00:00Z"},  # 오후
            {"created_at": "2026-01-03T19:00:00Z"},  # 저녁
        ]

        # When
        time_slots = service.analyze_time_slots(checkins)

        # Then: 모두 1회씩이므로 빈 리스트
        assert time_slots == []


class TestAverageSessionDuration:
    """평균 학습 세션 시간 계산 테스트."""

    def test_calculate_average_session_duration_normal(self):
        """테스트: 정상적인 평균 계산"""
        # Given: 2.0, 3.0, 4.0 시간
        service = LearningPatternService()
        checkins = [
            {"hours_studied": 2.0},
            {"hours_studied": 3.0},
            {"hours_studied": 4.0},
        ]

        # When
        avg = service.calculate_average_session_duration(checkins)

        # Then: 평균 3.0
        assert avg == 3.0

    def test_calculate_average_session_duration_empty(self):
        """테스트: 체크인 없을 시 0.0 반환"""
        # Given
        service = LearningPatternService()
        checkins = []

        # When
        avg = service.calculate_average_session_duration(checkins)

        # Then
        assert avg == 0.0

    def test_calculate_average_session_duration_missing_field(self):
        """테스트: hours_studied 필드 없을 시 제외"""
        # Given: 일부 체크인만 hours_studied 있음
        service = LearningPatternService()
        checkins = [
            {"hours_studied": 2.0},
            {"hours_studied": 4.0},
            {},  # hours_studied 없음
        ]

        # When
        avg = service.calculate_average_session_duration(checkins)

        # Then: (2.0 + 4.0) / 2 = 3.0
        assert avg == 3.0


class TestWeekdayEfficiency:
    """요일별 효율 분석 테스트."""

    def test_analyze_weekday_efficiency_normal(self):
        """테스트: 요일별 효율 정상 분석"""
        # Given: 월요일 5시간, 화요일 2시간, 수요일 4시간
        service = LearningPatternService()
        base_date = datetime(2026, 1, 5)  # 월요일

        checkins = [
            {
                "checkin_date": base_date.isoformat(),
                "hours_studied": 5.0,
            },  # 월요일
            {
                "checkin_date": (base_date + timedelta(days=1)).isoformat(),
                "hours_studied": 2.0,
            },  # 화요일
            {
                "checkin_date": (base_date + timedelta(days=2)).isoformat(),
                "hours_studied": 4.0,
            },  # 수요일
        ]

        # When
        best, worst = service.analyze_weekday_efficiency(checkins)

        # Then
        assert best == "월요일"
        assert worst == "화요일"

    def test_analyze_weekday_efficiency_insufficient_data(self):
        """테스트: 데이터 부족 시 None 반환"""
        # Given: 2개만
        service = LearningPatternService()
        checkins = [
            {"checkin_date": "2026-01-05", "hours_studied": 3.0},
            {"checkin_date": "2026-01-06", "hours_studied": 2.0},
        ]

        # When
        best, worst = service.analyze_weekday_efficiency(checkins)

        # Then
        assert best is None
        assert worst is None

    def test_analyze_weekday_efficiency_same_weekday_multiple_entries(self):
        """테스트: 같은 요일 여러 엔트리 평균"""
        # Given: 월요일 2회 (3시간, 5시간)
        service = LearningPatternService()
        base_date = datetime(2026, 1, 5)  # 월요일

        checkins = [
            {"checkin_date": base_date.isoformat(), "hours_studied": 3.0},
            {
                "checkin_date": (base_date + timedelta(days=7)).isoformat(),
                "hours_studied": 5.0,
            },  # 다음 주 월요일
            {
                "checkin_date": (base_date + timedelta(days=1)).isoformat(),
                "hours_studied": 2.0,
            },  # 화요일
        ]

        # When
        best, worst = service.analyze_weekday_efficiency(checkins)

        # Then: 월요일 평균 4.0, 화요일 2.0
        assert best == "월요일"
        assert worst == "화요일"


class TestMoodTrendAnalysis:
    """기분 추이 분석 테스트."""

    def test_analyze_mood_trend_improving(self):
        """테스트: 기분이 개선되는 추세"""
        # Given: stressed → okay → good → great
        service = LearningPatternService()
        checkins = [
            {"mood": "stressed"},
            {"mood": "okay"},
            {"mood": "good"},
            {"mood": "great"},
        ]

        # When
        trend = service.analyze_mood_trend(checkins)

        # Then
        assert trend == "improving"

    def test_analyze_mood_trend_declining(self):
        """테스트: 기분이 악화되는 추세"""
        # Given: great → good → okay → tired
        service = LearningPatternService()
        checkins = [
            {"mood": "great"},
            {"mood": "good"},
            {"mood": "okay"},
            {"mood": "tired"},
        ]

        # When
        trend = service.analyze_mood_trend(checkins)

        # Then
        assert trend == "declining"

    def test_analyze_mood_trend_stable(self):
        """테스트: 기분이 안정적인 추세"""
        # Given: good → good → okay → good
        service = LearningPatternService()
        checkins = [
            {"mood": "good"},
            {"mood": "good"},
            {"mood": "okay"},
            {"mood": "good"},
        ]

        # When
        trend = service.analyze_mood_trend(checkins)

        # Then
        assert trend == "stable"

    def test_analyze_mood_trend_insufficient_data(self):
        """테스트: 데이터 부족 시 stable 반환"""
        # Given: 2개만
        service = LearningPatternService()
        checkins = [
            {"mood": "good"},
            {"mood": "okay"},
        ]

        # When
        trend = service.analyze_mood_trend(checkins)

        # Then
        assert trend == "stable"


class TestConsistencyScore:
    """학습 일관성 점수 계산 테스트."""

    def test_calculate_consistency_score_very_consistent(self):
        """테스트: 매우 일관적인 학습 (CV < 0.3)"""
        # Given: 거의 같은 시간 학습
        service = LearningPatternService()
        checkins = [
            {"hours_studied": 2.9},
            {"hours_studied": 3.0},
            {"hours_studied": 3.1},
            {"hours_studied": 3.0},
            {"hours_studied": 2.9},
        ]

        # When
        score = service.calculate_consistency_score(checkins)

        # Then: 높은 점수 (70점 이상)
        assert score >= 70.0

    def test_calculate_consistency_score_inconsistent(self):
        """테스트: 일관성 없는 학습 (CV > 0.6)"""
        # Given: 시간이 크게 다름
        service = LearningPatternService()
        checkins = [
            {"hours_studied": 1.0},
            {"hours_studied": 5.0},
            {"hours_studied": 2.0},
            {"hours_studied": 6.0},
            {"hours_studied": 1.5},
        ]

        # When
        score = service.calculate_consistency_score(checkins)

        # Then: 낮은 점수 (40점 미만)
        assert score < 40.0

    def test_calculate_consistency_score_insufficient_data(self):
        """테스트: 데이터 부족 시 0.0 반환"""
        # Given: 2개만
        service = LearningPatternService()
        checkins = [
            {"hours_studied": 2.0},
            {"hours_studied": 3.0},
        ]

        # When
        score = service.calculate_consistency_score(checkins)

        # Then
        assert score == 0.0


class TestGetRecentMoods:
    """최근 기분 기록 추출 테스트."""

    def test_get_recent_moods_normal(self):
        """테스트: 최근 7개 기분 추출"""
        # Given: 10개 체크인
        service = LearningPatternService()
        checkins = [
            {"mood": "good"},
            {"mood": "okay"},
            {"mood": "great"},
            {"mood": "good"},
            {"mood": "tired"},
            {"mood": "good"},
            {"mood": "great"},
            {"mood": "okay"},
            {"mood": "good"},
            {"mood": "great"},
        ]

        # When
        recent_moods = service.get_recent_moods(checkins)

        # Then: 최근 7개
        assert len(recent_moods) == 7
        assert recent_moods[-1] == "great"

    def test_get_recent_moods_less_than_seven(self):
        """테스트: 7개 미만일 시 전체 반환"""
        # Given: 5개 체크인
        service = LearningPatternService()
        checkins = [
            {"mood": "good"},
            {"mood": "okay"},
            {"mood": "great"},
            {"mood": "good"},
            {"mood": "tired"},
        ]

        # When
        recent_moods = service.get_recent_moods(checkins)

        # Then: 전체 5개
        assert len(recent_moods) == 5


class TestAnalyzeLearningPattern:
    """학습 패턴 종합 분석 테스트."""

    def test_analyze_learning_pattern_comprehensive(self):
        """테스트: 종합 학습 패턴 분석"""
        # Given: 충분한 체크인 데이터
        service = LearningPatternService()
        base_date = datetime(2026, 1, 5, 9, 0)  # 월요일 오전

        checkins = [
            {
                "created_at": base_date.isoformat() + "Z",
                "checkin_date": base_date.date().isoformat(),
                "hours_studied": 3.0,
                "mood": "good",
            },
            {
                "created_at": (base_date + timedelta(days=1, hours=1)).isoformat()
                + "Z",
                "checkin_date": (base_date + timedelta(days=1)).date().isoformat(),
                "hours_studied": 2.5,
                "mood": "okay",
            },
            {
                "created_at": (base_date + timedelta(days=2)).isoformat() + "Z",
                "checkin_date": (base_date + timedelta(days=2)).date().isoformat(),
                "hours_studied": 3.2,
                "mood": "good",
            },
            {
                "created_at": (base_date + timedelta(days=3, hours=-1)).isoformat()
                + "Z",
                "checkin_date": (base_date + timedelta(days=3)).date().isoformat(),
                "hours_studied": 2.8,
                "mood": "great",
            },
        ]

        study_plan_id = "test-plan-123"

        # When
        pattern = service.analyze_learning_pattern(checkins, study_plan_id)

        # Then
        assert pattern["plan_id"] == study_plan_id
        assert "preferred_time_slots" in pattern
        assert pattern["average_session_duration"] > 0.0
        assert "consistency_score" in pattern
        assert pattern["mood_trend"] in ["improving", "stable", "declining"]
        assert len(pattern["recent_moods"]) > 0

    def test_analyze_learning_pattern_minimal_data(self):
        """테스트: 최소 데이터로 패턴 분석"""
        # Given: 3개 체크인
        service = LearningPatternService()
        checkins = [
            {
                "created_at": "2026-01-05T09:00:00Z",
                "checkin_date": "2026-01-05",
                "hours_studied": 3.0,
                "mood": "good",
            },
            {
                "created_at": "2026-01-06T10:00:00Z",
                "checkin_date": "2026-01-06",
                "hours_studied": 2.5,
                "mood": "okay",
            },
            {
                "created_at": "2026-01-07T09:00:00Z",
                "checkin_date": "2026-01-07",
                "hours_studied": 3.2,
                "mood": "good",
            },
        ]

        study_plan_id = "test-plan-456"

        # When
        pattern = service.analyze_learning_pattern(checkins, study_plan_id)

        # Then: 모든 필드가 존재하고 기본값 아님
        assert pattern["plan_id"] == study_plan_id
        assert pattern["average_session_duration"] > 0.0
        assert pattern["consistency_score"] >= 0.0
