"""학습 분석 서비스.

복합 진행도 계산, 이탈 위험 감지, 학습 패턴 분석 등의 비즈니스 로직을 제공합니다.
"""

from datetime import date, datetime, timedelta

from app.schemas.analytics import (
    LearnerStatus,
    ReviewUrgency,
    RiskSignal,
    RiskSignalType,
)


class AnalyticsService:
    """학습 분석 서비스."""

    def calculate_completion_rate(self, milestones: list[dict]) -> float:
        """마일스톤 완료율 계산.

        Args:
            milestones: 마일스톤 목록 (dict with "completed" key)

        Returns:
            float: 완료율 (0.0-100.0)
        """
        if not milestones:
            return 0.0

        completed_count = sum(1 for m in milestones if m.get("completed", False))
        total_count = len(milestones)

        return round((completed_count / total_count) * 100, 1)

    def calculate_time_adherence_rate(
        self, planned_hours: float, actual_hours: float
    ) -> float:
        """시간 이행률 계산.

        계획된 학습 시간 대비 실제 학습 시간의 비율.

        Args:
            planned_hours: 계획된 총 학습 시간
            actual_hours: 실제 학습 시간

        Returns:
            float: 시간 이행률 (%)
        """
        if planned_hours == 0:
            return 0.0

        return round((actual_hours / planned_hours) * 100, 1)

    def calculate_schedule_adherence_rate(
        self, start_date: date, target_date: date, current_progress: float
    ) -> float:
        """일정 준수율 계산.

        예상 진도 대비 실제 진도의 비율.

        Args:
            start_date: 학습 계획 시작일
            target_date: 목표 완료일
            current_progress: 현재 진행률 (%)

        Returns:
            float: 일정 준수율 (%)
        """
        today = date.today()

        # 전체 기간
        total_days = (target_date - start_date).days
        if total_days <= 0:
            return 0.0

        # 경과 일수
        elapsed_days = (today - start_date).days
        if elapsed_days < 0:
            elapsed_days = 0

        # 예상 진도율
        expected_progress = (elapsed_days / total_days) * 100

        if expected_progress == 0:
            return 0.0

        # 실제 진도 / 예상 진도
        return round((current_progress / expected_progress) * 100, 1)

    def predict_completion_date(
        self,
        target_date: date,
        current_progress: float,
        recent_daily_progress: float,
    ) -> date:
        """완료일 예측.

        현재 페이스를 유지할 경우 예상 완료일을 계산합니다.

        Args:
            target_date: 목표 완료일
            current_progress: 현재 진행률 (%)
            recent_daily_progress: 최근 일평균 진행률 (%)

        Returns:
            date: 예상 완료일
        """
        remaining_progress = 100.0 - current_progress

        if recent_daily_progress <= 0:
            # 진도가 없으면 목표일 + 30일 반환
            return target_date + timedelta(days=30)

        days_needed = remaining_progress / recent_daily_progress
        predicted_date = date.today() + timedelta(days=int(days_needed))

        return predicted_date

    def detect_streak_broken(self, last_checkin_date: date) -> list[RiskSignal]:
        """연속성 단절 감지.

        Args:
            last_checkin_date: 마지막 체크인 날짜

        Returns:
            list[RiskSignal]: 감지된 위험 신호 목록
        """
        days_since = (date.today() - last_checkin_date).days

        if days_since > 7:
            return [
                RiskSignal(
                    type=RiskSignalType.STREAK_BROKEN,
                    severity="high",
                    description=f"마지막 체크인 이후 {days_since}일 경과. 학습이 중단되었을 가능성이 높습니다.",
                    detected_at=datetime.now(),
                )
            ]

        return []

    def detect_time_decreased(
        self, daily_planned_hours: float, recent_avg_hours: float
    ) -> list[RiskSignal]:
        """학습 시간 급감 감지.

        Args:
            daily_planned_hours: 계획된 일일 학습 시간
            recent_avg_hours: 최근 7일 평균 학습 시간

        Returns:
            list[RiskSignal]: 감지된 위험 신호 목록
        """
        threshold = daily_planned_hours * 0.5

        if recent_avg_hours < threshold:
            severity = "high" if recent_avg_hours < threshold * 0.5 else "medium"

            return [
                RiskSignal(
                    type=RiskSignalType.TIME_DECREASED,
                    severity=severity,
                    description=f"최근 평균 학습 시간({recent_avg_hours:.1f}h)이 계획의 50% 미만입니다. 동기가 하락했을 수 있습니다.",
                    detected_at=datetime.now(),
                )
            ]

        return []

    def detect_mood_deteriorated(self, recent_moods: list[str]) -> list[RiskSignal]:
        """기분 악화 감지.

        연속 3회 이상 tired 또는 stressed면 번아웃 징후.

        Args:
            recent_moods: 최근 기분 목록 (시간순)

        Returns:
            list[RiskSignal]: 감지된 위험 신호 목록
        """
        if len(recent_moods) < 3:
            return []

        # 최근 3개
        last_three = recent_moods[-3:]
        negative_count = sum(1 for mood in last_three if mood in ["tired", "stressed"])

        if negative_count >= 3:
            return [
                RiskSignal(
                    type=RiskSignalType.MOOD_DETERIORATED,
                    severity="high",
                    description="최근 3회 연속 피곤함/스트레스 상태입니다. 번아웃 위험이 있습니다.",
                    detected_at=datetime.now(),
                )
            ]

        return []

    def classify_learner_status(
        self, schedule_adherence_rate: float, current_streak: int
    ) -> LearnerStatus:
        """학습자 상태 분류.

        Args:
            schedule_adherence_rate: 일정 준수율 (%)
            current_streak: 현재 연속 학습일

        Returns:
            LearnerStatus: 학습자 상태
        """
        # 이탈 위험: 일정 준수율 < 50% 또는 연속성 = 0
        if schedule_adherence_rate < 50.0 or current_streak == 0:
            return LearnerStatus.AT_RISK

        # 주의 필요: 50% ≤ 일정 준수율 < 80%
        if 50.0 <= schedule_adherence_rate < 80.0:
            return LearnerStatus.NEEDS_ATTENTION

        # 초과 달성: 일정 준수율 > 120%
        if schedule_adherence_rate > 120.0:
            return LearnerStatus.EXCEEDING

        # 정상 진행: 80% ≤ 일정 준수율 ≤ 120%
        return LearnerStatus.ON_TRACK

    def calculate_review_urgency(self, days_since_last_checkin: int) -> ReviewUrgency:
        """복습 긴급도 계산.

        Args:
            days_since_last_checkin: 마지막 체크인 이후 일수

        Returns:
            ReviewUrgency: 복습 긴급도
        """
        if days_since_last_checkin <= 7:
            return ReviewUrgency.LOW
        elif days_since_last_checkin <= 14:
            return ReviewUrgency.MEDIUM
        else:
            return ReviewUrgency.HIGH

    def generate_recommendations(
        self,
        status: LearnerStatus,
        schedule_adherence: float,
        time_adherence: float,
        risk_signals: list[RiskSignal],
    ) -> list[str]:
        """추천 액션 생성.

        Args:
            status: 학습자 상태
            schedule_adherence: 일정 준수율
            time_adherence: 시간 이행률
            risk_signals: 위험 신호 목록

        Returns:
            list[str]: 추천 액션 목록
        """
        recommendations = []

        if status == LearnerStatus.EXCEEDING:
            recommendations.append(
                f"현재 페이스를 유지하면 목표일보다 빠르게 완료할 수 있습니다! (진도: {schedule_adherence:.0f}%)"
            )
            if time_adherence > 120:
                recommendations.append(
                    "학습 시간이 계획보다 많습니다. 번아웃에 주의하세요."
                )

        elif status == LearnerStatus.ON_TRACK:
            recommendations.append(
                "계획대로 잘 진행 중입니다. 현재 페이스를 유지하세요!"
            )

        elif status == LearnerStatus.NEEDS_ATTENTION:
            recommendations.append(
                f"진도가 예상보다 느립니다 (진도: {schedule_adherence:.0f}%). 학습 시간을 늘리거나 목표일을 재조정하세요."
            )

        elif status == LearnerStatus.AT_RISK:
            recommendations.append(
                "이탈 위험이 있습니다. 학습을 재개하거나 계획을 재검토하세요."
            )

        # 위험 신호 기반 추천
        for signal in risk_signals:
            if signal.type == RiskSignalType.STREAK_BROKEN:
                recommendations.append("오늘부터 다시 학습을 시작해보세요!")
            elif signal.type == RiskSignalType.TIME_DECREASED:
                recommendations.append("학습 시간을 점진적으로 늘려보세요.")
            elif signal.type == RiskSignalType.MOOD_DETERIORATED:
                recommendations.append("휴식을 취하고 학습 계획을 재조정하세요.")

        return recommendations
