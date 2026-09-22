"""ChromaDB 전체 재인덱싱 스크립트.

기존 BGE-M3 임베딩을 OpenAI text-embedding-3-small로 교체합니다.

동작 순서:
1. ChromaDB 컬렉션 초기화 (clear_all)
2. MariaDB에서 enriched 자격증 전체 조회 (overview IS NOT NULL)
3. format_contextual_search_text + build_certificate_metadata로 텍스트/메타 준비
4. OpenAI text-embedding-3-small로 배치 임베딩 생성
5. ChromaDB에 upsert + MariaDB vector_id 동기화
6. 결과 리포트 출력

사용법:
    cd backend && uv run python -m scripts.reindex_all
"""

import logging
import sys
from pathlib import Path

from sqlalchemy.orm import sessionmaker

# backend 디렉토리를 path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.core.database import get_engine
from app.models.certificate import Certificate
from app.services.embedding.service import EmbeddingService
from app.services.embedding.vector_store import VectorStoreService

logger = logging.getLogger(__name__)

BATCH_SIZE = 32


def setup_logging():
    """로깅을 설정한다."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_session():
    """MariaDB 세션을 생성한다."""
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def main():
    """메인 엔트리 포인트."""
    setup_logging()

    settings = get_settings()
    logger.info("=" * 70)
    logger.info("ChromaDB 전체 재인덱싱 시작")
    logger.info(f"  임베딩 모델: {settings.OPENAI_EMBEDDING_MODEL}")
    logger.info(f"  임베딩 차원: {settings.OPENAI_EMBEDDING_DIMENSIONS}")
    logger.info(f"  ChromaDB: {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
    logger.info(f"  컬렉션: {settings.CHROMA_COLLECTION_NAME}")
    logger.info("=" * 70)

    session = get_session()
    embedding_service = EmbeddingService()

    try:
        # Step 1: MariaDB에서 enriched 자격증 조회
        results = (
            session.query(Certificate).filter(Certificate.overview.isnot(None)).all()
        )
        certificates = [cert.to_dict() for cert in results]
        logger.info(f"[Step 1] enriched 자격증 {len(certificates)}개 조회 완료")

        if not certificates:
            logger.info("재인덱싱할 자격증이 없습니다.")
            return

        # Step 2: ChromaDB 컬렉션 초기화
        vector_store = VectorStoreService(
            session=session,
            embedding_service=embedding_service,
        )
        deleted_count = vector_store.clear_all()
        logger.info(f"[Step 2] 기존 벡터 {deleted_count}개 삭제 완료")

        # clear_all()이 컬렉션을 재생성하므로 vector_store를 다시 생성
        vector_store = VectorStoreService(
            session=session,
            embedding_service=embedding_service,
        )

        # Step 3: 배치 임베딩 생성 + ChromaDB upsert
        total_uploaded = 0
        total_synced = 0
        total_failed = 0
        total_batches = (len(certificates) + BATCH_SIZE - 1) // BATCH_SIZE

        logger.info(
            f"[Step 3] {len(certificates)}개 자격증을 {total_batches}개 배치로 처리"
        )

        for i in range(0, len(certificates), BATCH_SIZE):
            batch = certificates[i : i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            logger.info(f"  배치 {batch_num}/{total_batches} ({len(batch)}개)")

            try:
                result = vector_store.upsert_certificates_batch_integrated(
                    batch, skip_existing=False
                )

                verified = result.get("verified_count", 0)
                failed_ids = result.get("failed_ids", [])
                total_uploaded += verified

                if failed_ids:
                    total_failed += len(failed_ids)
                    logger.warning(f"    검증 실패: {failed_ids[:3]}")

                # DB에 vector_id 동기화
                failed_set = set(failed_ids)
                certs_to_sync = [cert for cert in batch if cert["id"] not in failed_set]

                if certs_to_sync:
                    mappings = [(cert["id"], cert["id"]) for cert in certs_to_sync]
                    sync_result = vector_store.sync_vector_ids_to_db_batch(mappings)
                    synced = sync_result["success"]
                    total_synced += synced

                logger.info(f"    업로드: {verified}, 동기화: {len(certs_to_sync)}")

            except Exception as e:
                logger.error(f"    배치 처리 실패: {e}")
                total_failed += len(batch)
                continue

        # Step 4: 결과 리포트
        stats = vector_store.get_collection_stats()

        logger.info("=" * 70)
        logger.info("재인덱싱 완료")
        logger.info("=" * 70)
        logger.info(f"  대상 자격증: {len(certificates)}개")
        logger.info(f"  ChromaDB 업로드: {total_uploaded}개")
        logger.info(f"  DB vector_id 동기화: {total_synced}개")
        logger.info(f"  실패: {total_failed}개")
        logger.info(f"  ChromaDB 벡터 수: {stats['total_vectors']}개")
        logger.info("=" * 70)

    except Exception as e:
        logger.exception(f"재인덱싱 중 오류 발생: {e}")
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
