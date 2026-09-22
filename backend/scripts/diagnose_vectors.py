"""벡터 데이터 품질 진단 스크립트.

ChromaDB에 저장된 자격증 벡터의 품질과 메타데이터를 분석합니다.

사용법:
    uv run python -m scripts.diagnose_vectors
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.embedding.vector_store import VectorStoreService


def diagnose_vectors():
    """벡터 데이터 품질을 진단합니다."""
    print("=" * 80)
    print("벡터 데이터 품질 진단")
    print("=" * 80)
    print()

    try:
        # VectorStoreService 초기화
        vector_store = VectorStoreService()

        # 1. 컬렉션 통계
        stats = vector_store.get_collection_stats()
        print("[1] 컬렉션 통계")
        print("-" * 80)
        print(f"호스트: {stats['host']}:{stats['port']}")
        print(f"컬렉션: {stats['collection_name']}")
        print(f"총 벡터 수: {stats['total_vectors']}")
        print()

        # 2. 샘플 데이터 확인 (10개)
        print("[2] 샘플 벡터 메타데이터 (상위 10개)")
        print("-" * 80)
        vectors = vector_store.list_vectors(limit=10, include_embeddings=False)

        if not vectors:
            print("[경고] 벡터가 없습니다!")
            return

        # 메타데이터 필드 분석
        field_presence = {}

        for idx, vec in enumerate(vectors, 1):
            metadata = vec.get("metadata", {})
            vec_id = vec.get("id", "Unknown")

            print(f"\n#{idx} ID: {vec_id}")
            print(f"  title: {metadata.get('title', 'N/A')}")
            print(f"  series: {metadata.get('series', 'N/A')}")
            print(f"  difficulty: {metadata.get('difficulty', 'N/A')}")
            print(f"  study_period_days: {metadata.get('study_period_days', 'N/A')}")

            # 필드 존재 여부 집계
            for field in [
                "title",
                "series",
                "difficulty",
                "study_period_days",
                "industry",
                "related_jobs",
            ]:
                if field not in field_presence:
                    field_presence[field] = 0
                if metadata.get(field):
                    field_presence[field] += 1

        # 3. 메타데이터 완전성 분석
        print()
        print("[3] 메타데이터 필드 완전성 (상위 10개 샘플 기준)")
        print("-" * 80)
        for field, count in sorted(
            field_presence.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (count / len(vectors)) * 100
            print(f"  {field}: {count}/{len(vectors)} ({percentage:.0f}%)")

        # 4. 특정 도메인 검색 테스트
        print()
        print("[4] 검색 품질 테스트")
        print("-" * 80)

        test_queries = [
            ("IT 분야 취업 준비 비전공자", "IT"),
            ("금융 자격증 추천", "금융"),
            ("건설 산업기사", "건설"),
            ("미용사 자격증", "미용"),
        ]

        for query, expected_domain in test_queries:
            results = vector_store.search_records(
                namespace=VectorStoreService.NAMESPACE, query=query, top_k=5
            )

            print(f"\n쿼리: '{query}' (기대 도메인: {expected_domain})")
            if not results:
                print("  [경고] 검색 결과 없음!")
                continue

            for idx, result in enumerate(results[:3], 1):
                score = result.get("score", 0)
                metadata = result.get("metadata", {})
                title = metadata.get("title", "N/A")
                print(f"  #{idx} ({score:.3f}): {title}")

        # 5. 유사도 점수 분포 분석
        print()
        print("[5] 유사도 점수 분포 (IT 쿼리 기준)")
        print("-" * 80)

        it_results = vector_store.search_records(
            namespace=VectorStoreService.NAMESPACE,
            query="IT 소프트웨어 개발 프로그래밍 정보처리 취업",
            top_k=20,
        )

        if it_results:
            scores = [r.get("score", 0) for r in it_results]
            print(f"  최고: {max(scores):.3f}")
            print(f"  최저: {min(scores):.3f}")
            print(f"  평균: {sum(scores)/len(scores):.3f}")
            print(f"  중간: {sorted(scores)[len(scores)//2]:.3f}")

            # 임계값별 필터링 결과
            print()
            print("  임계값별 필터링 결과:")
            for threshold in [0.2, 0.25, 0.3, 0.35]:
                filtered = [s for s in scores if s >= threshold]
                print(f"    >= {threshold}: {len(filtered)}개")

        print()
        print("=" * 80)
        print("진단 완료!")
        print("=" * 80)

    except Exception as e:
        print(f"[오류] 진단 실패: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    diagnose_vectors()
