"""하이브리드 검색 테스트 (키워드 + 벡터)."""


class TestHybridSearch:
    """하이브리드 검색 테스트."""

    def test_keyword_matching_score(self):
        """키워드 매칭 점수 계산."""
        from app.services.study.hybrid_search import calculate_keyword_score

        # IT 쿼리
        query = "IT 소프트웨어 개발자 프로그래밍"

        # IT 자격증
        cert_text = "정보처리기사 소프트웨어 개발 프로그래밍 IT"
        score1 = calculate_keyword_score(query, cert_text)

        # 제조업 자격증
        cert_text2 = "금속재료기사 금속가공 제조"
        score2 = calculate_keyword_score(query, cert_text2)

        # IT 자격증 점수가 더 높아야 함
        assert score1 > score2
        assert score1 > 0.5
        assert score2 < 0.3

    def test_reciprocal_rank_fusion(self):
        """Reciprocal Rank Fusion 점수 계산."""
        from app.services.study.hybrid_search import reciprocal_rank_fusion

        # 벡터 검색 결과 (ID: 점수)
        vector_scores = {"1": 0.8, "2": 0.6, "3": 0.4, "4": 0.2}

        # 키워드 검색 결과
        keyword_scores = {"1": 0.5, "3": 0.9, "5": 0.7}

        # RRF 결합
        combined = reciprocal_rank_fusion(vector_scores, keyword_scores)

        # ID 1은 양쪽에 모두 있으므로 높은 점수
        assert "1" in combined
        assert combined["1"] > combined.get("2", 0)
        assert combined["1"] > combined.get("4", 0)

        # ID 3도 양쪽에 있음
        assert "3" in combined

        # ID 5는 키워드만 있음
        assert "5" in combined

    def test_hybrid_search_integration(self):
        """하이브리드 검색 통합 테스트."""
        from app.services.study.hybrid_search import HybridSearcher

        searcher = HybridSearcher()

        # 테스트 데이터
        certificates = [
            {"id": "1", "title": "정보처리기사", "overview": "소프트웨어 개발"},
            {"id": "2", "title": "금속재료기사", "overview": "금속 가공"},
            {"id": "3", "title": "정보처리기능사", "overview": "IT 기초"},
        ]

        # 벡터 점수 (제조업이 높음)
        vector_scores = {"1": 0.5, "2": 0.8, "3": 0.4}

        # 하이브리드 검색
        query = "IT 소프트웨어 개발"
        results = searcher.hybrid_search(
            query=query,
            certificates=certificates,
            vector_scores=vector_scores,
        )

        # IT 자격증이 상위권이어야 함 (최소 1개)
        top_ids = [r["id"] for r in results[:2]]
        it_cert_ids = ["1", "3"]  # 정보처리기사, 정보처리기능사
        it_in_top2 = sum(1 for cert_id in it_cert_ids if cert_id in top_ids)

        # 상위 2개 중 최소 1개는 IT 자격증이어야 함
        assert it_in_top2 >= 1
