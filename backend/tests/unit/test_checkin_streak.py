"""Unit tests for checkin streak calculation.

매월 1일 크래시 버그(B-01) 수정을 검증하는 테스트.
streak 계산 로직이 월 경계를 올바르게 처리하는지 확인합니다.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch


def make_mock_checkin(checkin_date: date, hours: float = 1.0) -> MagicMock:
    """테스트용 mock checkin 객체 생성."""
    mock = MagicMock()
    mock.checkin_date = checkin_date
    mock.hours_studied = hours
    mock.user_id = "test-user"
    mock.study_plan_id = "test-plan"
    return mock


class TestStreakOnFirstDayOfMonth:
    """매월 1일에 streak 계산이 크래시하지 않는지 검증."""

    @patch("app.api.v1.checkins.date")
    def test_streak_on_first_of_month_with_yesterday_checkin(self, mock_date):
        """1월 1일에 12월 31일 체크인이 있을 때 크래시하지 않아야 함."""
        from app.api.v1.checkins import get_checkin_stats

        # today = 2월 1일
        mock_date.today.return_value = date(2026, 2, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "test-user"

        # 1월 31일에 체크인 (어제)
        checkin = make_mock_checkin(date(2026, 1, 31))
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [checkin]
        mock_db.query.return_value = mock_query

        # 크래시 없이 실행되어야 함
        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            get_checkin_stats(db=mock_db, user=mock_user)
        )

        assert result.current_streak == 1
        assert result.total_days == 1

    @patch("app.api.v1.checkins.date")
    def test_streak_on_march_first_with_feb_checkin(self, mock_date):
        """3월 1일에 2월 28일 체크인 - 월 경계 테스트."""
        from app.api.v1.checkins import get_checkin_stats

        mock_date.today.return_value = date(2026, 3, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "test-user"

        checkin = make_mock_checkin(date(2026, 2, 28))
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = [checkin]
        mock_db.query.return_value = mock_query

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            get_checkin_stats(db=mock_db, user=mock_user)
        )

        assert result.current_streak == 1

    @patch("app.api.v1.checkins.date")
    def test_streak_on_first_of_month_no_checkins(self, mock_date):
        """1일에 체크인이 없을 때 정상 반환."""
        from app.api.v1.checkins import get_checkin_stats

        mock_date.today.return_value = date(2026, 2, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "test-user"

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            get_checkin_stats(db=mock_db, user=mock_user)
        )

        assert result.current_streak == 0
        assert result.total_days == 0


class TestStreakCalculation:
    """streak 계산의 일반적인 정확성 검증."""

    @patch("app.api.v1.checkins.date")
    def test_consecutive_days_streak(self, mock_date):
        """3일 연속 체크인 시 current_streak=3."""
        from app.api.v1.checkins import get_checkin_stats

        today = date(2026, 2, 15)
        mock_date.today.return_value = today
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = "test-user"

        checkins = [
            make_mock_checkin(today),
            make_mock_checkin(today - timedelta(days=1)),
            make_mock_checkin(today - timedelta(days=2)),
        ]

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = checkins
        mock_db.query.return_value = mock_query

        import asyncio

        result = asyncio.get_event_loop().run_until_complete(
            get_checkin_stats(db=mock_db, user=mock_user)
        )

        assert result.current_streak == 3
        assert result.longest_streak == 3
