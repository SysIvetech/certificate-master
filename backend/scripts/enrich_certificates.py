"""LLM으로 자격증 정보를 보강하는 스크립트.

Supabase에서 MariaDB로 마이그레이션됨 (2026-01-21).

동작 순서:
1. MariaDB에서 자격증 조회
2. SearXNG API로 정보 검색
3. LLM(OpenAI)으로 정제
4. MariaDB 업데이트

사용법:
    # 테스트용 단일 보강
    uv run python -m scripts.enrich_certificates --test

    # 특정 자격증 ID 보강
    uv run python -m scripts.enrich_certificates --id <certificate_id>

    # 미보강 자격증 N개 보강
    uv run python -m scripts.enrich_certificates --limit 10

    # 모든 미보강 자격증 보강
    uv run python -m scripts.enrich_certificates --all
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import get_engine
from app.models.certificate import Certificate
from app.services.enrichment_service import get_enrichment_service


def get_mariadb_session() -> Session:
    """MariaDB 세션을 생성한다."""
    from sqlalchemy.orm import sessionmaker

    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def get_unenriched_certificates(
    session: Session, limit: Optional[int] = None
) -> list[dict]:
    """미보강 자격증 목록을 조회한다.

    Args:
        session: SQLAlchemy 세션
        limit: 최대 조회 개수

    Returns:
        자격증 딕셔너리 리스트
    """
    query = session.query(Certificate).filter(Certificate.overview.is_(None))

    if limit:
        query = query.limit(limit)

    results = query.all()
    return [cert.to_dict() for cert in results]


def get_certificate_by_id(session: Session, cert_id: str) -> dict | None:
    """ID로 자격증을 조회한다.

    Args:
        session: SQLAlchemy 세션
        cert_id: 자격증 ID

    Returns:
        자격증 딕셔너리 또는 None
    """
    result = session.query(Certificate).filter(Certificate.id == cert_id).first()

    if result:
        return result.to_dict()
    return None


async def test_single_certificate():
    """Test enrichment on a single certificate."""
    print("=" * 70)
    print("테스트 모드: 첫 번째 미보강 자격증 보강")
    print("=" * 70)

    session = get_mariadb_session()

    try:
        # Get first unenriched certificate
        certs = get_unenriched_certificates(session, limit=1)

        if not certs:
            print("\n[오류] 보강할 자격증을 찾지 못했습니다.")
            return

        cert = certs[0]
        print(f"\n자격증 ID: {cert['id']}")
        print(f"자격증명: {cert['title']}")

        # Enrich
        service = get_enrichment_service(session)
        result = await service.enrich_certificate(
            cert["id"],
            cert["title"],
        )

        # Display results
        print("\n" + "=" * 70)
        print("보강 결과")
        print("=" * 70)
        print(f"상태: {result['status']}")

        if result["status"] == "success":
            enrichment = result["enrichment"]
            print(f"\n개요:\n{enrichment['overview']}")
            print(f"\n난이도: {enrichment['difficulty']}/5")
            print(f"준비 기간: {enrichment['study_period_days']}일")

            print("\n시험 정보:")
            exam_info = enrichment.get("exam_info", {})
            if exam_info.get("subjects"):
                print(f"  과목: {', '.join(exam_info['subjects'][:3])}")
            print(f"  유형: {exam_info.get('exam_type', 'N/A')}")
            print(f"  합격 기준: {exam_info.get('passing_criteria', 'N/A')}")
            print(f"  응시료: {exam_info.get('total_fee', 'N/A')}")

            print("\n커리어/후기 정보:")
            print(
                f"  커리어 활용 사례: {len(enrichment.get('career_info', {}).get('use_cases', []))}개"
            )
            print(
                f"  후기 요약 여부: {bool(enrichment.get('user_reviews', {}).get('summary'))}"
            )
            print(
                f"  공식 사이트 여부: {bool(enrichment.get('official_sources', {}).get('official_site'))}"
            )

            print(f"\n추천 강의: {len(enrichment['recommended_lectures'])}개")
            for idx, lec in enumerate(enrichment["recommended_lectures"][:3], 1):
                print(
                    f"  [{idx}] {lec['platform']} - {lec['title'][:40]}... (점수: {lec.get('relevance_score', 0):.2f})"
                )
        else:
            print(f"\n[오류] {result['error']}")

        print("\n" + "=" * 70)

    finally:
        session.close()


async def enrich_by_id(certificate_id: str):
    """Enrich specific certificate by ID."""
    print(f"\n자격증 보강 시작: {certificate_id}")

    session = get_mariadb_session()

    try:
        # Get certificate
        cert = get_certificate_by_id(session, certificate_id)

        if not cert:
            print(f"[오류] 자격증을 찾을 수 없습니다: {certificate_id}")
            return

        service = get_enrichment_service(session)

        result = await service.enrich_certificate(
            cert["id"],
            cert["title"],
        )

        print(f"\n결과: {result['status']}")
        if result["status"] == "error":
            print(f"오류: {result['error']}")

    finally:
        session.close()


async def enrich_batch(limit: Optional[int] = None):
    """Enrich multiple certificates in batch."""
    session = get_mariadb_session()

    try:
        # Get unenriched certificates
        certificates = get_unenriched_certificates(session, limit=limit)

        if not certificates:
            print("\n[확인] 미보강 자격증이 없습니다.")
            return

        print(f"\n미보강 자격증 {len(certificates)}개 발견")

        if limit:
            print(f"앞에서부터 {limit}개만 처리합니다")

        # Enrich in batch
        service = get_enrichment_service(session)
        results = []
        for cert in certificates:
            result = await service.enrich_certificate(cert["id"], cert["title"])
            results.append((cert["title"], result))

        # Summary
        print("\n" + "=" * 70)
        print("배치 보강 결과")
        print("=" * 70)

        successful = sum(1 for _, r in results if r.get("status") == "success")
        failed = sum(1 for _, r in results if r.get("status") == "error")

        print(f"총 건수: {len(results)}")
        print(f"성공: {successful}")
        print(f"실패: {failed}")

        if failed > 0:
            print("\n실패한 자격증:")
            for title, result in results:
                if result.get("status") == "error":
                    print(f"  - {title}: {result.get('error', '알 수 없는 오류')}")

        print("=" * 70)

    finally:
        session.close()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="LLM으로 자격증 정보를 보강합니다")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: enrich single certificate",
    )
    parser.add_argument(
        "--id",
        type=str,
        help="Enrich specific certificate by ID",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Enrich first N unenriched certificates",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Enrich all unenriched certificates",
    )

    args = parser.parse_args()

    # Validate arguments
    if not (args.test or args.id or args.limit or args.all):
        parser.error("Must specify --test, --id, --limit, or --all")

    try:
        if args.test:
            asyncio.run(test_single_certificate())
        elif args.id:
            asyncio.run(enrich_by_id(args.id))
        elif args.limit or args.all:
            limit = args.limit if not args.all else None
            asyncio.run(enrich_batch(limit))

    except KeyboardInterrupt:
        print("\n\n[경고] 사용자가 작업을 중단했습니다.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[오류] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
