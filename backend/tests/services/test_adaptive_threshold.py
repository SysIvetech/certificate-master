"""적응형 유사도 임계값 테스트."""


class TestAdaptiveThreshold:
    """적응형 임계값 계산 테스트."""

    def test_high_quality_results_increase_threshold(self):
        """높은 품질 결과는 임계값을 높여야 함."""
        from app.services.study.adaptive_threshold import calculate_adaptive_threshold

        # 최고 유사도가 0.7인 경우 (높은 품질)
        scores = [0.70, 0.65, 0.60, 0.55, 0.50]
        threshold = calculate_adaptive_threshold(scores)

        # 기본값 0.3보다 높아야 함
        assert threshold > 0.3
        # 하지만 0.5를 넘지 않아야 함 (너무 엄격하지 않게)
        assert threshold <= 0.5

    def test_low_quality_results_decrease_threshold(self):
        """낮은 품질 결과는 임계값을 낮춰야 함."""
        from app.services.study.adaptive_threshold import calculate_adaptive_threshold

        # 최고 유사도가 0.35인 경우 (낮은 품질)
        scores = [0.35, 0.33, 0.31, 0.29, 0.27]
        threshold = calculate_adaptive_threshold(scores)

        # 기본값 0.3보다 낮아야 함
        assert threshold < 0.3
        # 하지만 절대 최소값 0.2 이상이어야 함
        assert threshold >= 0.2

    def test_medium_quality_results_keep_default(self):
        """중간 품질 결과는 기본 임계값 유지."""
        from app.services.study.adaptive_threshold import calculate_adaptive_threshold

        # 최고 유사도가 0.45인 경우 (중간 품질)
        scores = [0.45, 0.43, 0.41, 0.39, 0.37]
        threshold = calculate_adaptive_threshold(scores)

        # 기본값 0.3 근처 (0.25-0.35 범위)
        assert 0.25 <= threshold <= 0.35

    def test_empty_scores_return_default(self):
        """빈 결과는 기본 임계값 반환."""
        from app.services.study.adaptive_threshold import calculate_adaptive_threshold

        scores = []
        threshold = calculate_adaptive_threshold(scores)

        # 기본값 0.3
        assert threshold == 0.3

    def test_very_high_quality_caps_at_max(self):
        """매우 높은 품질도 최대값에 제한."""
        from app.services.study.adaptive_threshold import calculate_adaptive_threshold

        # 최고 유사도가 0.9인 경우
        scores = [0.90, 0.85, 0.80, 0.75, 0.70]
        threshold = calculate_adaptive_threshold(scores)

        # 최대값 0.5를 넘지 않음
        assert threshold <= 0.5

    def test_threshold_filters_low_scores(self):
        """계산된 임계값이 낮은 점수를 필터링해야 함."""
        from app.services.study.adaptive_threshold import calculate_adaptive_threshold

        # 높은 품질 결과
        scores = [0.70, 0.65, 0.60, 0.55, 0.50, 0.30, 0.25, 0.20]
        threshold = calculate_adaptive_threshold(scores)

        # 임계값 이상의 점수만 유효
        filtered = [s for s in scores if s >= threshold]

        # 낮은 점수들(0.30, 0.25, 0.20)은 필터링되어야 함
        assert 0.30 not in filtered
        assert 0.25 not in filtered
        assert 0.20 not in filtered
