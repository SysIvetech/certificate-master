"""기존 DB 데이터의 difficulty-study_period_days 비일관성 보정 스크립트 테스트."""

from scripts.fix_inconsistent_difficulty import (
    DIFFICULTY_PERIOD_RANGES,
    compute_fix,
    find_inconsistent_records,
)


class TestFindInconsistentRecords:
    """비일관 레코드 탐지 테스트."""

    def test_consistent_record_not_flagged(self):
        """정합성이 맞는 레코드는 비일관으로 탐지되지 않는다."""
        records = [
            {"id": 1, "title": "A", "difficulty": 3, "study_period_days": 90},
        ]
        result = find_inconsistent_records(records)
        assert len(result) == 0

    def test_inconsistent_record_flagged(self):
        """정합성이 맞지 않는 레코드는 탐지된다."""
        records = [
            {"id": 1, "title": "A", "difficulty": 4, "study_period_days": 2},
        ]
        result = find_inconsistent_records(records)
        assert len(result) == 1
        assert result[0]["id"] == 1

    def test_null_values_not_flagged(self):
        """difficulty나 study_period_days가 None이면 탐지하지 않는다."""
        records = [
            {"id": 1, "title": "A", "difficulty": None, "study_period_days": 90},
            {"id": 2, "title": "B", "difficulty": 3, "study_period_days": None},
        ]
        result = find_inconsistent_records(records)
        assert len(result) == 0

    def test_mixed_records(self):
        """정합/비일관 레코드가 섞여있을 때 비일관만 반환."""
        records = [
            {"id": 1, "title": "OK", "difficulty": 2, "study_period_days": 60},
            {"id": 2, "title": "BAD", "difficulty": 1, "study_period_days": 365},
            {"id": 3, "title": "OK2", "difficulty": 5, "study_period_days": 500},
        ]
        result = find_inconsistent_records(records)
        assert len(result) == 1
        assert result[0]["id"] == 2


class TestComputeFix:
    """보정값 계산 테스트."""

    def test_clamps_to_min(self):
        """study_period_days가 범위 미만이면 최솟값으로 보정."""
        fix = compute_fix(difficulty=4, study_period_days=2)
        assert fix == 150  # difficulty=4 최솟값

    def test_clamps_to_max(self):
        """study_period_days가 범위 초과이면 최댓값으로 보정."""
        fix = compute_fix(difficulty=1, study_period_days=365)
        assert fix == 21  # difficulty=1 최댓값

    def test_in_range_unchanged(self):
        """범위 내 값은 변경 없음."""
        fix = compute_fix(difficulty=3, study_period_days=120)
        assert fix == 120

    def test_all_difficulty_levels(self):
        """모든 난이도에 대해 보정이 범위 내로 들어간다."""
        for diff, (min_d, max_d) in DIFFICULTY_PERIOD_RANGES.items():
            # 범위 미만
            assert compute_fix(diff, 0) == min_d
            # 범위 초과
            assert compute_fix(diff, 9999) == max_d
            # 범위 내
            mid = (min_d + max_d) // 2
            assert compute_fix(diff, mid) == mid
