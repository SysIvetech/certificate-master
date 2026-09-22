"""리랭킹 효과 테스트 (LLM 호출 없음).

벡터 검색 결과가 리랭킹으로 어떻게 재정렬되는지 확인합니다.
"""

from app.services.study.reranker import DomainReranker

from app.models.certificate import Certificate


def test_reranking_effect():
    """리랭킹 전후 비교."""
    print("=" * 80)
    print("리랭킹 효과 테스트: IT 분야")
    print("=" * 80)

    # 샘플 자격증 (실제 테스트 결과 기반)
    certificates = [
        Certificate(
            id=1,
            title="제품응용모델링산업기사",
            series="산업기사",
            difficulty=3,
            study_period_days=90,
            career_info={"industry": ["제조", "CAD"]},
        ),
        Certificate(
            id=2,
            title="철골기능사",
            series="기능사",
            difficulty=2,
            study_period_days=60,
            career_info={"industry": ["건설", "제조"]},
        ),
        Certificate(
            id=3,
            title="전산응용건축제도기능사",
            series="기능사",
            difficulty=2,
            study_period_days=60,
            career_info={"industry": ["건설", "건축"]},
        ),
        Certificate(
            id=4,
            title="정보처리기능사",
            series="기능사",
            difficulty=2,
            study_period_days=60,
            career_info={"industry": ["IT", "정보처리"]},
        ),
        Certificate(
            id=5,
            title="정보처리기사",
            series="기사",
            difficulty=3,
            study_period_days=90,
            career_info={"industry": ["IT", "정보처리"]},
        ),
    ]

    # 벡터 유사도 점수 (제조업이 높음 - 문제 상황 재현)
    vector_scores = {
        1: 0.450,  # 제품응용모델링
        2: 0.445,  # 철골
        3: 0.440,  # 건축제도
        4: 0.400,  # 정보처리기능사
        5: 0.395,  # 정보처리기사
    }

    print("\n[벡터 유사도 순위] (리랭킹 전)")
    print("-" * 80)
    sorted_by_vector = sorted(
        certificates, key=lambda c: vector_scores.get(c.id, 0), reverse=True
    )
    for idx, cert in enumerate(sorted_by_vector, 1):
        score = vector_scores.get(cert.id, 0)
        print(f"{idx}. {cert.title} (유사도: {score:.3f})")

    # 리랭킹
    reranker = DomainReranker()
    user_domains = ["IT개발"]

    reranked = reranker.rerank(
        certificates=certificates,
        vector_scores=vector_scores,
        user_domains=user_domains,
    )

    print("\n[리랭킹 후 순위]")
    print("-" * 80)
    for idx, cert in enumerate(reranked, 1):
        vector_score = vector_scores.get(cert.id, 0)
        final_score = reranker.calculate_final_score(
            certificate=cert,
            vector_similarity=vector_score,
            user_domains=user_domains,
        )
        boost = final_score - vector_score
        print(
            f"{idx}. {cert.title} "
            f"(유사도: {vector_score:.3f}, 최종: {final_score:.3f}, "
            f"부스트: {boost:+.3f})"
        )

    print("\n[결과 분석]")
    print("-" * 80)
    # IT 자격증이 상위권에 있는지 확인
    top_3_ids = [cert.id for cert in reranked[:3]]
    it_cert_ids = [4, 5]

    it_in_top3 = len([cid for cid in it_cert_ids if cid in top_3_ids])
    print(f"상위 3개 중 IT 자격증: {it_in_top3}개")

    if it_in_top3 >= 2:
        print("[SUCCESS] Reranking worked: IT certificates moved to top!")
    else:
        print("[FAIL] Reranking failed: IT certificates still in bottom.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_reranking_effect()
