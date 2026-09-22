"""빠른 리랭킹 테스트 (실제 DB 데이터 사용).

LLM 호출 없이 실제 벡터 검색 → 리랭킹 효과만 확인합니다.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.study.reranker import DomainReranker
from sqlalchemy.orm import sessionmaker

from app.core.database import get_engine
from app.models.certificate import Certificate as CertModel
from app.services.embedding.vector_store import VectorStoreService


def quick_test():
    """빠른 리랭킹 테스트."""
    print("=" * 80)
    print("Quick Reranking Test: IT Query")
    print("=" * 80)

    # 데이터베이스 세션
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # IT 쿼리 (쿼리 생성 프롬프트 개선 효과 반영)
        it_query = (
            "IT software developer system engineer database administrator "
            "web developer information processing programming coding "
            "job preparation entry-level non-major self-study beginner "
            "basic industrial engineer technician 3 months short-term "
            "NOT: manufacturing welding machining metal woodwork cooking beauty tourism"
        )

        print("\n[Query]")
        print(f"{it_query[:100]}...")

        # 벡터 검색
        print("\n[Vector Search]")
        vector_store = VectorStoreService()
        results = vector_store.search_records(
            namespace=VectorStoreService.NAMESPACE,
            query=it_query,
            top_k=40,
        )
        print(f"Found {len(results)} results")

        if not results:
            print("No results found!")
            return

        # 자격증 ID로 상세 정보 조회
        cert_ids = [r["id"] for r in results]
        certificates = db.query(CertModel).filter(CertModel.id.in_(cert_ids)).all()

        # 벡터 점수 매핑
        vector_scores = {r["id"]: r["score"] for r in results}

        print("\n[Top 10 - BEFORE Reranking]")
        print("-" * 80)
        sorted_by_vector = sorted(
            certificates, key=lambda c: vector_scores.get(c.id, 0), reverse=True
        )
        for idx, cert in enumerate(sorted_by_vector[:10], 1):
            score = vector_scores.get(cert.id, 0)
            industry = cert.career_info.get("industry", []) if cert.career_info else []
            print(
                f"{idx:2d}. {cert.title:30s} (score: {score:.3f}) [{', '.join(industry[:2])}]"
            )

        # 리랭킹
        print("\n[Reranking...]")
        reranker = DomainReranker()
        user_domains = ["IT개발"]

        # Certificate 모델 객체 리스트
        vector_score_dict = {
            cert.id: vector_scores.get(cert.id, 0) for cert in certificates
        }
        reranked = reranker.rerank(
            certificates=certificates,
            vector_scores=vector_score_dict,
            user_domains=user_domains,
        )

        print("\n[Top 10 - AFTER Reranking]")
        print("-" * 80)
        for idx, cert in enumerate(reranked[:10], 1):
            vector_score = vector_scores.get(cert.id, 0)
            final_score = reranker.calculate_final_score(
                certificate=cert,
                vector_similarity=vector_score,
                user_domains=user_domains,
            )
            boost = final_score - vector_score
            industry = cert.career_info.get("industry", []) if cert.career_info else []
            print(
                f"{idx:2d}. {cert.title:30s} "
                f"(vec: {vector_score:.3f}, final: {final_score:.3f}, "
                f"boost: {boost:+.3f}) [{', '.join(industry[:2])}]"
            )

        # IT 자격증 분석
        print("\n[Analysis]")
        print("-" * 80)
        it_keywords = ["정보처리", "소프트웨어", "프로그래밍", "컴퓨터"]

        # Before
        before_it_count = 0
        for cert in sorted_by_vector[:10]:
            if any(kw in cert.title for kw in it_keywords):
                before_it_count += 1

        # After
        after_it_count = 0
        for cert in reranked[:10]:
            if any(kw in cert.title for kw in it_keywords):
                after_it_count += 1

        print("IT certificates in top 10:")
        print(f"  Before reranking: {before_it_count}/10")
        print(f"  After reranking:  {after_it_count}/10")

        if after_it_count > before_it_count:
            print(
                f"\n[SUCCESS] Reranking improved IT ranking (+{after_it_count - before_it_count})"
            )
        else:
            print("\n[WARNING] No improvement in IT ranking")

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    quick_test()
