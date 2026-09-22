"""적응형 임계값 효과 테스트."""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.study.adaptive_threshold import calculate_adaptive_threshold


def test_adaptive_threshold():
    """적응형 임계값 효과 시연."""
    print("=" * 80)
    print("Adaptive Threshold Effect Test")
    print("=" * 80)

    test_cases = [
        {
            "name": "High Quality Results",
            "scores": [0.75, 0.70, 0.65, 0.60, 0.55, 0.50, 0.45, 0.40, 0.35, 0.30],
            "description": "Very relevant results (max: 0.75)",
        },
        {
            "name": "Medium Quality Results",
            "scores": [0.50, 0.48, 0.46, 0.44, 0.42, 0.40, 0.38, 0.36, 0.34, 0.32],
            "description": "Moderately relevant results (max: 0.50)",
        },
        {
            "name": "Low Quality Results",
            "scores": [0.35, 0.33, 0.31, 0.29, 0.27, 0.25, 0.23, 0.21, 0.19, 0.17],
            "description": "Weakly relevant results (max: 0.35)",
        },
    ]

    for case in test_cases:
        print(f"\n[{case['name']}]")
        print(f"{case['description']}")
        print("-" * 80)

        scores = case["scores"]
        threshold = calculate_adaptive_threshold(scores)
        filtered = [s for s in scores if s >= threshold]

        print(f"Original scores: {len(scores)} results")
        print(f"  Range: {min(scores):.2f} - {max(scores):.2f}")
        print(f"\nAdaptive threshold: {threshold:.2f}")
        print("  (Default would be: 0.30)")
        print(f"\nFiltered scores: {len(filtered)} results")
        print(f"  Kept: {', '.join(f'{s:.2f}' for s in filtered[:5])}...")
        print(f"  Removed: {', '.join(f'{s:.2f}' for s in scores if s < threshold)}")

        # 효과 분석
        default_threshold = 0.30
        default_filtered = [s for s in scores if s >= default_threshold]

        print("\nComparison with default threshold (0.30):")
        print(f"  Default: {len(default_filtered)} results")
        print(f"  Adaptive: {len(filtered)} results")

        diff = len(filtered) - len(default_filtered)
        if diff > 0:
            print(f"  Effect: +{diff} more results (more lenient)")
        elif diff < 0:
            print(f"  Effect: {diff} fewer results (more strict)")
        else:
            print("  Effect: No change (same as default)")

    print("\n" + "=" * 80)
    print("Summary:")
    print("- High quality: Stricter threshold (0.4-0.5) to keep only best")
    print("- Medium quality: Default threshold (0.3) maintained")
    print("- Low quality: Lenient threshold (0.2-0.25) to include more")
    print("=" * 80)


if __name__ == "__main__":
    test_adaptive_threshold()
