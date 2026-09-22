"""하이브리드 검색 효과 테스트."""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.study.hybrid_search import HybridSearcher


def test_hybrid_effect():
    """하이브리드 검색 효과 시연."""
    print("=" * 80)
    print("Hybrid Search Effect Test")
    print("=" * 80)

    # IT 쿼리
    query = "IT 소프트웨어 개발자 프로그래밍"

    # 테스트 자격증
    certificates = [
        {
            "id": "1",
            "title": "정보처리기사",
            "overview": "소프트웨어 개발 및 정보처리 전문가",
        },
        {
            "id": "2",
            "title": "제품응용모델링산업기사",
            "overview": "CAD를 활용한 제품 모델링",
        },
        {
            "id": "3",
            "title": "정보처리기능사",
            "overview": "IT 기초 프로그래밍",
        },
    ]

    print(f"\n[Query]: {query}")
    print("\n[Certificates]")
    for cert in certificates:
        print(f"  - {cert['title']}: {cert['overview']}")

    # 벡터 점수 (제조업이 높음 - 문제 상황)
    vector_scores = {"1": 0.45, "2": 0.50, "3": 0.40}

    print("\n[Vector Scores Only]")
    print("-" * 80)
    sorted_by_vector = sorted(
        certificates, key=lambda c: vector_scores.get(c["id"], 0), reverse=True
    )
    for idx, cert in enumerate(sorted_by_vector, 1):
        score = vector_scores.get(cert["id"], 0)
        print(f"{idx}. {cert['title']} (vector: {score:.2f})")

    # 하이브리드 검색 (가중치 평균 방식)
    searcher = HybridSearcher(keyword_weight=0.3, vector_weight=0.7)
    results = searcher.hybrid_search_weighted(query, certificates, vector_scores)

    print("\n[Hybrid Search (Vector + Keyword)]")
    print("-" * 80)
    for idx, cert in enumerate(results, 1):
        print(
            f"{idx}. {cert['title']} "
            f"(hybrid: {cert['hybrid_score']:.4f}, "
            f"vector: {cert['vector_score']:.2f}, "
            f"keyword: {cert['keyword_score']:.2f})"
        )

    # 분석
    print("\n[Analysis]")
    print("-" * 80)

    # IT 자격증 순위 비교
    it_cert_ids = ["1", "3"]

    # 벡터만
    vector_ranks = {cert["id"]: idx + 1 for idx, cert in enumerate(sorted_by_vector)}
    it_avg_rank_vector = sum(vector_ranks[cid] for cid in it_cert_ids) / len(
        it_cert_ids
    )

    # 하이브리드
    hybrid_ranks = {cert["id"]: idx + 1 for idx, cert in enumerate(results)}
    it_avg_rank_hybrid = sum(hybrid_ranks[cid] for cid in it_cert_ids) / len(
        it_cert_ids
    )

    print("IT 자격증 평균 순위:")
    print(f"  Vector only: {it_avg_rank_vector:.1f}")
    print(f"  Hybrid:      {it_avg_rank_hybrid:.1f}")
    print(f"  Improvement: {it_avg_rank_vector - it_avg_rank_hybrid:+.1f}")

    if it_avg_rank_hybrid < it_avg_rank_vector:
        print("\n[SUCCESS] 하이브리드 검색이 IT 자격증 순위를 개선했습니다!")
    else:
        print("\n[WARNING] 순위 개선이 미미합니다.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_hybrid_effect()
