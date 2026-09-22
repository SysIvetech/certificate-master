"""학습 패턴 분석 서비스.

체크인 데이터를 기반으로 학습자의 패턴을 분석합니다.
"""

from collections import Counter
from datetime import datetime
from statistics import mean, stdev
from typing import Optional


class LearningPatternService:
    """학습 패턴 분석 서비스."""

    def analyze_time_slots(self, checkins: list[dict]) -> list[str]:
        """선호 학습 시간대 분석.

        Args:
            checkins: 체크인 데이터 리스트 (created_at 포함)

        Returns:
            선호 시간대 리스트 (예: ["오전", "저녁"])
        """
        if not checkins:
            return []

        time_slots = []
        for checkin in checkins:
            created_at = checkin.get("created_at")
            if not created_at:
                continue

            # ISO 형식 파싱
            try:
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                hour = dt.hour

                # 시간대 분류
                if 6 <= hour < 12:
                    time_slots.append("오전")
                elif 12 <= hour < 18:
                    time_slots.append("오후")
                elif 18 <= hour < 24:
                    time_slots.append("저녁")
                else:
                    time_slots.append("새벽")
            except (ValueError, AttributeError):
                continue

        # 빈도 순으로 정렬
        if not time_slots:
            return []

        counter = Counter(time_slots)
        # 최소 2회 이상 발생한 시간대만 반환
        return [slot for slot, count in counter.most_common() if count >= 2]

    def calculate_average_session_duration(self, checkins: list[dict]) -> float:
        """평균 학습 세션 시간 계산.

        Args:
            checkins: 체크인 데이터 리스트 (hours_studied 포함)

        Returns:
            평균 학습 시간 (시간 단위)
        """
        if not checkins:
            return 0.0

        hours_list = [
            c.get("hours_studied", 0.0)
            for c in checkins
            if c.get("hours_studied") is not None
        ]

        if not hours_list:
            return 0.0

        return round(mean(hours_list), 2)

    def analyze_weekday_efficiency(
        self, checkins: list[dict]
    ) -> tuple[Optional[str], Optional[str]]:
        """요일별 효율 분석.

        학습 시간이 가장 많은 요일과 가장 적은 요일을 찾습니다.

        Args:
            checkins: 체크인 데이터 리스트 (checkin_date, hours_studied 포함)

        Returns:
            (best_weekday, worst_weekday) 튜플
        """
        if len(checkins) < 3:
            return (None, None)

        weekday_hours: dict[str, list[float]] = {
            "월요일": [],
            "화요일": [],
            "수요일": [],
            "목요일": [],
            "금요일": [],
            "토요일": [],
            "일요일": [],
        }

        for checkin in checkins:
            checkin_date = checkin.get("checkin_date")
            hours_studied = checkin.get("hours_studied")

            if not checkin_date or hours_studied is None:
                continue

            try:
                # ISO 형식 날짜 파싱
                dt = datetime.fromisoformat(checkin_date)
                weekday_names = [
                    "월요일",
                    "화요일",
                    "수요일",
                    "목요일",
                    "금요일",
                    "토요일",
                    "일요일",
                ]
                weekday = weekday_names[dt.weekday()]

                weekday_hours[weekday].append(hours_studied)
            except (ValueError, AttributeError):
                continue

        # 평균 학습 시간 계산
        weekday_avg = {
            day: mean(hours) if hours else 0.0 for day, hours in weekday_hours.items()
        }

        # 데이터가 있는 요일만 필터링
        valid_weekdays = {day: avg for day, avg in weekday_avg.items() if avg > 0.0}

        if not valid_weekdays:
            return (None, None)

        best_weekday = max(valid_weekdays, key=valid_weekdays.get)
        worst_weekday = min(valid_weekdays, key=valid_weekdays.get)

        return (best_weekday, worst_weekday)

    def analyze_mood_trend(self, checkins: list[dict]) -> str:
        """기분 추이 분석.

        최근 체크인의 기분 변화를 분석합니다.

        Args:
            checkins: 체크인 데이터 리스트 (mood 포함)

        Returns:
            "improving", "stable", "declining" 중 하나
        """
        if len(checkins) < 3:
            return "stable"

        # 최근 7개 체크인만 분석
        recent_checkins = checkins[-7:] if len(checkins) >= 7 else checkins

        moods = [c.get("mood") for c in recent_checkins if c.get("mood")]

        if len(moods) < 3:
            return "stable"

        # 기분 점수 매핑
        mood_scores = {
            "great": 5,
            "good": 4,
            "okay": 3,
            "tired": 2,
            "stressed": 1,
        }

        scores = [mood_scores.get(mood, 3) for mood in moods]

        # 추세 분석 (선형 회귀 간단 버전)
        n = len(scores)
        if n < 2:
            return "stable"

        # 평균 기울기 계산
        first_half_avg = mean(scores[: n // 2])
        second_half_avg = mean(scores[n // 2 :])

        diff = second_half_avg - first_half_avg

        if diff > 0.5:
            return "improving"
        elif diff < -0.5:
            return "declining"
        else:
            return "stable"

    def get_recent_moods(self, checkins: list[dict]) -> list[str]:
        """최근 7일 기분 기록 추출.

        Args:
            checkins: 체크인 데이터 리스트 (mood 포함)

        Returns:
            최근 7개 기분 리스트
        """
        recent_checkins = checkins[-7:] if len(checkins) >= 7 else checkins
        return [c.get("mood") for c in recent_checkins if c.get("mood")]

    def calculate_consistency_score(self, checkins: list[dict]) -> float:
        """학습 일관성 점수 계산.

        학습 시간의 표준편차가 작을수록 높은 점수를 부여합니다.

        Args:
            checkins: 체크인 데이터 리스트 (hours_studied 포함)

        Returns:
            일관성 점수 (0.0 ~ 100.0)
        """
        if len(checkins) < 3:
            return 0.0

        hours_list = [
            c.get("hours_studied", 0.0)
            for c in checkins
            if c.get("hours_studied") is not None
        ]

        if len(hours_list) < 3:
            return 0.0

        avg_hours = mean(hours_list)
        if avg_hours == 0.0:
            return 0.0

        # 표준편차 계산
        try:
            std_hours = stdev(hours_list)
        except ValueError:
            return 0.0

        # 변동 계수 (CV) 계산: std / mean
        cv = std_hours / avg_hours if avg_hours > 0 else 0.0

        # CV가 작을수록 일관성이 높음
        # CV 0.0 ~ 0.3: 매우 일관적 (100 ~ 70점)
        # CV 0.3 ~ 0.6: 보통 (70 ~ 40점)
        # CV 0.6 ~: 일관성 낮음 (40 ~ 0점)
        if cv <= 0.3:
            score = 100 - (cv / 0.3) * 30
        elif cv <= 0.6:
            score = 70 - ((cv - 0.3) / 0.3) * 30
        else:
            score = max(0, 40 - ((cv - 0.6) / 0.4) * 40)

        return round(score, 2)

    def analyze_learning_pattern(
        self, checkins: list[dict], study_plan_id: str
    ) -> dict:
        """학습 패턴 종합 분석.

        Args:
            checkins: 체크인 데이터 리스트
            study_plan_id: 학습 계획 UUID

        Returns:
            LearningPattern 스키마 형태의 딕셔너리
        """
        # 시간대 분석
        preferred_time_slots = self.analyze_time_slots(checkins)

        # 평균 세션 시간
        average_session_duration = self.calculate_average_session_duration(checkins)

        # 요일별 효율
        best_weekday, worst_weekday = self.analyze_weekday_efficiency(checkins)

        # 기분 추이
        mood_trend = self.analyze_mood_trend(checkins)
        recent_moods = self.get_recent_moods(checkins)

        # 일관성 점수
        consistency_score = self.calculate_consistency_score(checkins)

        return {
            "plan_id": study_plan_id,
            "preferred_time_slots": preferred_time_slots,
            "average_session_duration": average_session_duration,
            "best_weekday": best_weekday,
            "worst_weekday": worst_weekday,
            "mood_trend": mood_trend,
            "recent_moods": recent_moods,
            "consistency_score": consistency_score,
        }
