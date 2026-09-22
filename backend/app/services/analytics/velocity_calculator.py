"""
학습 속도 계산 서비스

학습 계획의 진행 속도, 예상 완료일, 속도 상태를 계산합니다.
"""

from datetime import date, datetime, timedelta
from typing import Dict, List, Optional


class VelocityCalculator:
    """
    학습 계획 진행 상황을 분석하고 속도 지표를 계산합니다.

    Attributes:
        plan: created_at, target_date, milestones를 포함한 학습 계획 딕셔너리
        snapshots: 진행 스냅샷 목록(최신 순)
    """

    def __init__(self, study_plan: Dict, progress_snapshots: List[Dict]):
        """
        속도 계산기를 초기화합니다.

        Args:
            study_plan: created_at, target_date, milestones를 포함한 학습 계획 데이터
            progress_snapshots: 진행 스냅샷 기록 목록(최신→과거 순)
        """
        self.plan = study_plan
        self.snapshots = progress_snapshots

    def calculate_expected_progress(self, current_date: Optional[date] = None) -> float:
        """
        선형 일정 기준 예상 진행률을 계산합니다.

        Args:
            current_date: 계산 기준일(기본값: 오늘)

        Returns:
            예상 진행률(0-100)
        """
        if current_date is None:
            current_date = date.today()

        # Get start and target dates
        created_at = self.plan["created_at"]
        if isinstance(created_at, datetime):
            start_date = created_at.date()
        elif isinstance(created_at, str):
            start_date = datetime.fromisoformat(created_at).date()
        else:
            start_date = created_at

        target_date_str = self.plan["target_date"]
        if isinstance(target_date_str, str):
            target_date = datetime.fromisoformat(target_date_str).date()
        else:
            target_date = target_date_str

        # Calculate linear progress
        total_days = (target_date - start_date).days
        if total_days <= 0:
            return 100.0

        elapsed_days = (current_date - start_date).days
        if elapsed_days <= 0:
            return 0.0

        if elapsed_days >= total_days:
            return 100.0

        expected_pct = (elapsed_days / total_days) * 100
        return expected_pct

    def calculate_actual_progress(self) -> float:
        """
        마일스톤 완료 상태로 실제 진행률을 계산합니다.

        Returns:
            실제 진행률(0-100)
        """
        milestones = self.plan.get("milestones", [])
        if not milestones:
            # Fallback to progress_percentage if no milestones
            return self.plan.get("progress_percentage", 0.0)

        completed_count = sum(1 for m in milestones if m.get("completed", False))
        total_count = len(milestones)

        if total_count == 0:
            return 0.0

        return (completed_count / total_count) * 100

    def calculate_velocity(self) -> float:
        """
        진행 속도(일당 퍼센트 포인트)를 계산합니다.

        진행 스냅샷을 이용해 속도를 산출합니다.

        Returns:
            일일 진행 속도(%/day)
        """
        if not self.snapshots or len(self.snapshots) < 2:
            return 0.0

        # Get newest and oldest snapshots
        newest = self.snapshots[0]
        oldest = self.snapshots[-1]

        # Calculate time difference
        newest_date = newest["snapshot_date"]
        oldest_date = oldest["snapshot_date"]

        if isinstance(newest_date, str):
            newest_date = datetime.fromisoformat(newest_date).date()
        if isinstance(oldest_date, str):
            oldest_date = datetime.fromisoformat(oldest_date).date()

        days_diff = (newest_date - oldest_date).days

        if days_diff == 0:
            return 0.0

        # Calculate progress difference
        progress_diff = newest["progress_percentage"] - oldest["progress_percentage"]

        return progress_diff / days_diff

    def predict_completion_date(self) -> date:
        """
        현재 속도를 기반으로 완료일을 예측합니다.

        Returns:
            예측 완료일
        """
        velocity = self.calculate_velocity()

        # If velocity is zero or negative, return target date
        if velocity <= 0:
            target_date_str = self.plan["target_date"]
            if isinstance(target_date_str, str):
                return datetime.fromisoformat(target_date_str).date()
            return target_date_str

        # Calculate remaining progress
        current_progress = self.calculate_actual_progress()
        remaining_progress = 100 - current_progress

        # Calculate days needed at current velocity
        days_needed = remaining_progress / velocity

        # Use most recent snapshot date if available, otherwise today
        base_date = date.today()
        if self.snapshots and len(self.snapshots) > 0:
            snapshot_date = self.snapshots[0]["snapshot_date"]
            if isinstance(snapshot_date, str):
                base_date = datetime.fromisoformat(snapshot_date).date()
            else:
                base_date = snapshot_date

        # Add to base date
        predicted = base_date + timedelta(days=int(days_needed))

        return predicted

    def get_velocity_status(self) -> Dict:
        """
        종합 속도 상태를 반환합니다.

        Returns:
            속도 지표와 상태를 담은 딕셔너리:
                - expected_progress: 예상 진행률(%)
                - actual_progress: 실제 진행률(%)
                - progress_delta: 차이(실제 - 예상)
                - velocity: 진행 속도(%/day)
                - predicted_date: ISO 날짜 문자열
                - status: 'ahead' | 'on-track' | 'behind' | 'critical'
        """
        expected = self.calculate_expected_progress()
        actual = self.calculate_actual_progress()
        delta = actual - expected
        velocity = self.calculate_velocity()
        predicted = self.predict_completion_date()

        # Determine status
        if delta > 10:
            status = "ahead"
        elif delta > -5:
            status = "on-track"
        elif delta > -15:
            status = "behind"
        else:
            status = "critical"

        return {
            "expected_progress": round(expected, 1),
            "actual_progress": round(actual, 1),
            "progress_delta": round(delta, 1),
            "velocity": round(velocity, 2),
            "predicted_date": predicted.isoformat(),
            "status": status,
        }
