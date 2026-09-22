"""데이터 파이프라인: 자격증 보강 + 임베딩 생성 통합 스크립트.

Supabase에서 MariaDB로 마이그레이션됨 (2026-01-21).

동작 순서:
1. [Enrich] MariaDB에서 미보강 자격증 조회 → 웹 검색 → LLM 정제 → DB 업데이트
2. [Embedding] 보강된 자격증 조회 → OpenAI 임베딩 생성 → ChromaDB 업로드

============================================================
Provider 설정 (.env.local 또는 CLI 인자)
============================================================

검색:
  - searxng : SearXNG 메타 검색 (기본값, 무료)
              └─ 설치: docker run -d -p 8888:8080 searxng/searxng

임베딩:
  - OpenAI text-embedding-3-small (기본값, 유료)

LLM:
  - GPT-4o-mini (OpenAI API) 사용

============================================================
기본 사용법
============================================================

# 테스트 (1개만 처리, .env.local 설정 사용)
uv run python -m scripts.data_pipeline --test

# 특정 개수만 처리
uv run python -m scripts.data_pipeline --limit 10

# 모든 미보강 자격증 처리
uv run python -m scripts.data_pipeline --all

# 보강만 실행 (임베딩 건너뛰기)
uv run python -m scripts.data_pipeline --limit 10 --skip-embedding

# 임베딩만 실행 (보강 건너뛰기)
uv run python -m scripts.data_pipeline --limit 10 --skip-enrich

# 이미 임베딩된 자격증 건너뛰기
uv run python -m scripts.data_pipeline --all --skip-existing

# 실패한 자격증 재시도
uv run python -m scripts.data_pipeline --retry

============================================================
SearXNG 최적화 설정
============================================================

# searxng/settings.yml (Docker 볼륨 마운트 후 편집)
server:
  limiter: false  # 로컬이므로 제한 해제
search:
  safe_search: 0
  autocomplete: ""
  default_lang: "ko-KR"

============================================================
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, TypedDict

from sqlalchemy.orm import Session
from tqdm import tqdm

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import get_engine
from app.models.certificate import Certificate

# ============================================================
# 로깅 설정
# ============================================================

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """로깅을 설정한다.

    Args:
        verbose: True면 DEBUG 레벨, False면 INFO 레벨.
    """
    level = logging.DEBUG if verbose else logging.INFO
    format_str = "%(asctime)s [%(levelname)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=level,
        format=format_str,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # 이미 설정된 로거 재설정
    )

    # 라이브러리 로그 억제 (불필요한 내부 로그 제거)
    # trafilatura: "discarding data: None", "download error" 등
    logging.getLogger("trafilatura").setLevel(logging.CRITICAL)
    # urllib3: "Retrying (Retry...)" SSL 재시도 로그
    logging.getLogger("urllib3").setLevel(logging.CRITICAL)
    # httpx: "HTTP Request: GET ..." 매 요청마다 출력
    logging.getLogger("httpx").setLevel(logging.WARNING)
    # httpcore: httpx 내부 로그
    logging.getLogger("httpcore").setLevel(logging.WARNING)


# ============================================================
# 타입 정의
# ============================================================


class EnrichResult(TypedDict):
    """보강 단계 결과."""

    processed: int
    success: int
    failed: int
    failed_ids: list[str]
    skipped: bool


class EmbeddingResult(TypedDict):
    """임베딩 단계 결과."""

    processed: int
    uploaded: int
    synced: int
    skipped: int
    synced_from_chroma: int
    failed_ids: list[str]
    skipped_step: bool


class PipelineResult(TypedDict):
    """파이프라인 전체 결과."""

    enrich: EnrichResult
    embedding: EmbeddingResult


# ============================================================
# 실패 레코드 관리
# ============================================================

FAILED_RECORDS_DIR = Path(__file__).parent / "failed_records"


def save_failed_records(
    step: str, failed_certs: list[dict], error_messages: dict[str, str]
) -> Path:
    """실패한 자격증 목록을 JSON 파일로 저장한다.

    Args:
        step: 실패한 단계 ("enrich" 또는 "embedding").
        failed_certs: 실패한 자격증 목록.
        error_messages: 자격증 ID별 에러 메시지.

    Returns:
        저장된 파일 경로.
    """
    FAILED_RECORDS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"failed_{step}_{timestamp}.json"
    filepath = FAILED_RECORDS_DIR / filename

    data = {
        "step": step,
        "timestamp": datetime.now().isoformat(),
        "count": len(failed_certs),
        "certificates": [
            {
                "id": cert["id"],
                "title": cert["title"],
                "error": error_messages.get(cert["id"], "Unknown error"),
            }
            for cert in failed_certs
        ],
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"실패 레코드 저장됨: {filepath}")
    return filepath


def load_latest_failed_records(step: Optional[str] = None) -> Optional[dict]:
    """가장 최근 실패 레코드를 로드한다.

    Args:
        step: 특정 단계만 로드 ("enrich" 또는 "embedding"). None이면 전체.

    Returns:
        실패 레코드 딕셔너리 또는 None.
    """
    if not FAILED_RECORDS_DIR.exists():
        return None

    pattern = f"failed_{step}_*.json" if step else "failed_*.json"
    files = sorted(FAILED_RECORDS_DIR.glob(pattern), reverse=True)

    if not files:
        return None

    with open(files[0], "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 유틸리티 함수
# ============================================================


def get_mariadb_session() -> Session:
    """MariaDB 세션을 생성한다."""
    from sqlalchemy.orm import sessionmaker

    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


# ============================================================
# 데이터 파이프라인 클래스
# ============================================================


class DataPipeline:
    """데이터 파이프라인: 보강 → 임베딩 순서 실행."""

    BATCH_SIZE = 32
    TEST_COLLECTION_NAME = "certificates-test"  # 테스트용 컬렉션 이름

    def __init__(
        self,
        test_mode: bool = False,
    ):
        """파이프라인 초기화.

        Args:
            test_mode: 테스트 모드 여부. True이면 별도 컬렉션 사용하여 프로덕션 데이터와 격리.

        Note:
            검색 서비스는 SearXNG를 기본값으로 사용합니다.
            임베딩은 OpenAI text-embedding-3-small을 사용합니다.
        """
        self.test_mode = test_mode
        self._collection_name = self.TEST_COLLECTION_NAME if test_mode else None

    # --------------------------------------------------------
    # 보강 단계
    # --------------------------------------------------------

    async def enrich_step(
        self,
        limit: Optional[int] = None,
        cert_ids: Optional[list[str]] = None,
    ) -> EnrichResult:
        """보강 단계 실행.

        Args:
            limit: 처리할 최대 자격증 수.
            cert_ids: 특정 자격증 ID 목록 (재시도용).

        Returns:
            처리 결과.
        """
        from app.services.enrichment_service import get_enrichment_service

        logger.info("=" * 70)
        logger.info("[STEP 1/2] 자격증 보강 (Enrich)")
        logger.info("=" * 70)

        session = get_mariadb_session()
        failed_certs: list[dict] = []
        error_messages: dict[str, str] = {}

        try:
            # 자격증 조회
            if cert_ids:
                # 특정 ID만 조회 (재시도)
                query = session.query(Certificate).filter(Certificate.id.in_(cert_ids))
                logger.info(f"재시도 대상: {len(cert_ids)}개 자격증")
            else:
                # 미보강 자격증 조회
                query = session.query(Certificate).filter(
                    Certificate.overview.is_(None)
                )
                if limit:
                    query = query.limit(limit)

            results = query.all()

            if not results:
                logger.info("보강할 자격증이 없습니다.")
                return EnrichResult(
                    processed=0,
                    success=0,
                    failed=0,
                    failed_ids=[],
                    skipped=False,
                )

            certificates = [cert.to_dict() for cert in results]
            logger.info(f"미보강 자격증 {len(certificates)}개 발견")

            # 검색 서비스 생성 (SearXNG 기본값)
            from app.services.search_factory import get_search_service

            search_service = get_search_service()
            logger.info(f"  검색 서비스: {search_service.provider_name}")

            # 보강 실행
            service = get_enrichment_service(session, search_service=search_service)
            logger.info(
                f"  LLM 서비스: {service.llm.provider_name} ({service.llm.model})"
            )
            success = 0
            failed = 0

            # tqdm 진행률 표시
            pbar = tqdm(certificates, desc="보강 처리", unit="건")

            for cert in pbar:
                pbar.set_postfix_str(cert["title"][:20])
                try:
                    result = await service.enrich_certificate(cert["id"], cert["title"])
                    if result.get("status") == "success":
                        success += 1
                        logger.debug(f"[성공] {cert['title']}")
                    else:
                        failed += 1
                        error_msg = result.get("error", "알 수 없는 오류")
                        error_messages[cert["id"]] = error_msg
                        failed_certs.append(cert)
                        logger.warning(f"[실패] {cert['title']}: {error_msg}")
                except Exception as e:
                    failed += 1
                    error_messages[cert["id"]] = str(e)
                    failed_certs.append(cert)
                    logger.error(f"[오류] {cert['title']}: {str(e)}")

            pbar.close()

            # 실패 레코드 저장
            if failed_certs:
                save_failed_records("enrich", failed_certs, error_messages)

            logger.info(f"보강 완료: 성공 {success}개, 실패 {failed}개")
            return EnrichResult(
                processed=len(certificates),
                success=success,
                failed=failed,
                failed_ids=[c["id"] for c in failed_certs],
                skipped=False,
            )

        finally:
            session.close()

    # --------------------------------------------------------
    # 임베딩 단계 - Private 메서드
    # --------------------------------------------------------

    def _query_certificates(
        self, session: Session, limit: Optional[int]
    ) -> tuple[list[dict], list[dict]]:
        """DB에서 자격증을 조회한다.

        Args:
            session: DB 세션.
            limit: 검증용 조회 제한.

        Returns:
            (vector_id 없는 자격증, vector_id 있는 자격증) 튜플.
        """
        # vector_id가 없는 것: 전부 조회 (데이터 일관성 보장)
        query_without = session.query(Certificate).filter(
            Certificate.overview.isnot(None),
            Certificate.vector_id.is_(None),
        )
        results_without = query_without.all()

        # vector_id가 있는 것: 검증용 조회
        query_with = session.query(Certificate).filter(
            Certificate.overview.isnot(None),
            Certificate.vector_id.isnot(None),
        )
        if limit and len(results_without) == 0:
            results_with = query_with.limit(limit).all()
        else:
            results_with = query_with.all()

        certs_without = [cert.to_dict() for cert in results_without]
        certs_with = [cert.to_dict() for cert in results_with]

        return certs_without, certs_with

    def _classify_by_chroma_status(
        self, vector_store, certs_without_vector_id: list[dict]
    ) -> tuple[list[dict], list[dict]]:
        """ChromaDB 존재 여부로 자격증을 분류한다.

        Args:
            vector_store: VectorStoreService 인스턴스.
            certs_without_vector_id: vector_id가 없는 자격증 목록.

        Returns:
            (동기화만 필요한 것, 새로 생성 필요한 것) 튜플.
        """
        if not certs_without_vector_id:
            return [], []

        ids_to_check = [c["id"] for c in certs_without_vector_id]
        existing_in_chroma = set(vector_store.check_existing_vectors(ids_to_check))

        certs_to_sync_only = []  # ChromaDB에 있지만 MariaDB에 vector_id 없음
        certs_truly_missing = []  # ChromaDB에도 없음

        for cert in certs_without_vector_id:
            if cert["id"] in existing_in_chroma:
                certs_to_sync_only.append(cert)
            else:
                certs_truly_missing.append(cert)

        if certs_to_sync_only:
            logger.info(
                f"  ChromaDB에 이미 존재 (동기화만 필요): {len(certs_to_sync_only)}개"
            )
        if certs_truly_missing:
            logger.info(
                f"  ChromaDB에 없음 (새로 생성 필요): {len(certs_truly_missing)}개"
            )

        return certs_to_sync_only, certs_truly_missing

    def _sync_existing_from_chroma(
        self, vector_store, certs_to_sync_only: list[dict]
    ) -> int:
        """ChromaDB에 존재하는 자격증의 vector_id를 동기화한다.

        Args:
            vector_store: VectorStoreService 인스턴스.
            certs_to_sync_only: 동기화할 자격증 목록.

        Returns:
            동기화된 개수.
        """
        if not certs_to_sync_only:
            return 0

        logger.info(
            f"ChromaDB에 존재하는 {len(certs_to_sync_only)}개 자격증의 "
            "vector_id 동기화 중..."
        )
        mappings = [(cert["id"], cert["id"]) for cert in certs_to_sync_only]
        sync_result = vector_store.sync_vector_ids_to_db_batch(mappings)
        synced = sync_result["success"]
        logger.info(f"  DB에 vector_id {synced}개 동기화 완료")
        return synced

    def _find_orphan_certs(
        self, vector_store, certs_with_vector_id: list[dict]
    ) -> tuple[list[dict], int]:
        """ChromaDB에 없는 고아 레코드를 찾는다.

        Args:
            vector_store: VectorStoreService 인스턴스.
            certs_with_vector_id: vector_id가 있는 자격증 목록.

        Returns:
            (고아 자격증 목록, 이미 동기화된 개수) 튜플.
        """
        if not certs_with_vector_id:
            return [], 0

        ids_to_check = [c["vector_id"] for c in certs_with_vector_id]
        existing_in_chroma = set(vector_store.check_existing_vectors(ids_to_check))

        orphan_certs = []
        already_synced = 0

        for cert in certs_with_vector_id:
            if cert["vector_id"] in existing_in_chroma:
                already_synced += 1
            else:
                orphan_certs.append(cert)

        if orphan_certs:
            logger.warning(
                f"ChromaDB에 없는 고아 레코드: {len(orphan_certs)}개 → 재생성 예정"
            )

        return orphan_certs, already_synced

    def _process_embedding_batches(
        self,
        vector_store,
        certificates: list[dict],
        certs_truly_missing: list[dict],
        orphan_certs: list[dict],
    ) -> tuple[int, int, list[str]]:
        """배치로 임베딩을 생성하고 업로드한다.

        Args:
            vector_store: VectorStoreService 인스턴스.
            certificates: 처리할 자격증 목록.
            certs_truly_missing: 신규 생성 대상.
            orphan_certs: 재생성 대상.

        Returns:
            (업로드 개수, 동기화 개수, 실패 ID 목록) 튜플.
        """
        total_uploaded = 0
        total_synced = 0
        all_failed_ids: list[str] = []

        total_batches = (len(certificates) + self.BATCH_SIZE - 1) // self.BATCH_SIZE

        logger.info(
            f"처리 대상: {len(certificates)}개 "
            f"(신규 {len(certs_truly_missing)} + 재생성 {len(orphan_certs)})"
        )

        # tqdm 진행률 표시
        pbar = tqdm(
            range(0, len(certificates), self.BATCH_SIZE),
            desc="임베딩 생성",
            unit="배치",
            total=total_batches,
        )

        for i in pbar:
            batch = certificates[i : i + self.BATCH_SIZE]
            batch_num = (i // self.BATCH_SIZE) + 1
            pbar.set_postfix_str(f"배치 {batch_num}/{total_batches}")

            try:
                # 처리 대상 로깅
                for cert in batch:
                    status = "재생성" if cert.get("vector_id") else "신규"
                    logger.debug(
                        f"  [{status}] {cert['title']} (ID: {cert['id'][:8]}...)"
                    )

                # 임베딩 + 업로드
                result = vector_store.upsert_certificates_batch_integrated(
                    batch, skip_existing=True
                )

                verified = result.get("verified_count", 0)
                skipped = result.get("skipped_count", 0)
                failed_ids = result.get("failed_ids", [])

                if skipped > 0:
                    logger.debug(f"  ChromaDB에 이미 존재: {skipped}개 스킵")

                if verified > 0:
                    logger.debug(f"  ChromaDB에 {verified}개 업로드 완료")
                    total_uploaded += verified

                if failed_ids:
                    logger.warning(f"  검증 실패: {failed_ids[:3]}")
                    all_failed_ids.extend(failed_ids)

                # DB에 vector_id 동기화
                skipped_set = set(result.get("skipped_ids", []))
                failed_set = set(failed_ids)
                certs_to_sync = [
                    cert
                    for cert in batch
                    if cert["id"] not in skipped_set and cert["id"] not in failed_set
                ]

                if certs_to_sync:
                    mappings = [(cert["id"], cert["id"]) for cert in certs_to_sync]
                    sync_result = vector_store.sync_vector_ids_to_db_batch(mappings)
                    sync_count = sync_result["success"]
                    total_synced += sync_count
                    logger.debug(f"  DB에 vector_id {sync_count}개 동기화")

            except Exception as e:
                logger.error(f"배치 처리 실패: {str(e)}")
                # 배치 전체를 실패로 처리
                all_failed_ids.extend([c["id"] for c in batch])
                continue

        pbar.close()
        return total_uploaded, total_synced, all_failed_ids

    # --------------------------------------------------------
    # 임베딩 단계 - 메인 메서드
    # --------------------------------------------------------

    async def embedding_step(
        self,
        limit: Optional[int] = None,
        skip_existing: bool = False,
        cert_ids: Optional[list[str]] = None,
    ) -> EmbeddingResult:
        """임베딩 단계 실행.

        Args:
            limit: 검증용 조회 제한.
            skip_existing: 이미 임베딩된 자격증 건너뛰기.
            cert_ids: 특정 자격증 ID 목록 (재시도용).

        Returns:
            처리 결과.
        """
        from app.services.embedding.service import EmbeddingService
        from app.services.embedding.vector_store import VectorStoreService

        logger.info("=" * 70)
        logger.info("[STEP 2/2] 임베딩 생성 (Embedding)")
        logger.info("=" * 70)

        # OpenAI 임베딩 서비스 생성
        embedding_service = EmbeddingService()
        logger.info(f"  임베딩 서비스: {type(embedding_service).__name__}")

        session = get_mariadb_session()

        try:
            # 세션 및 임베딩 서비스 주입으로 DI 패턴 적용
            # 테스트 모드에서는 별도 컬렉션 사용
            vector_store = VectorStoreService(
                session=session,
                embedding_service=embedding_service,
                collection_name=self._collection_name,
            )
            if self.test_mode:
                logger.info(
                    f"  ⚠️  테스트 모드: '{self.TEST_COLLECTION_NAME}' 컬렉션 사용"
                )

            # 1단계: 자격증 조회
            if cert_ids:
                # 재시도: 특정 ID만 처리
                query = session.query(Certificate).filter(Certificate.id.in_(cert_ids))
                results = query.all()
                certs_without_vector_id = [cert.to_dict() for cert in results]
                certs_with_vector_id = []
                logger.info(f"재시도 대상: {len(certs_without_vector_id)}개 자격증")
            else:
                certs_without_vector_id, certs_with_vector_id = (
                    self._query_certificates(session, limit)
                )

            all_certificates = certs_without_vector_id + certs_with_vector_id

            if not all_certificates:
                logger.info("보강된 자격증이 없습니다.")
                return EmbeddingResult(
                    processed=0,
                    uploaded=0,
                    synced=0,
                    skipped=0,
                    synced_from_chroma=0,
                    failed_ids=[],
                    skipped_step=False,
                )

            logger.info(f"보강된 자격증 {len(all_certificates)}개 발견")
            logger.info(f"  MariaDB vector_id 없음: {len(certs_without_vector_id)}개")
            logger.info(f"  MariaDB vector_id 있음: {len(certs_with_vector_id)}개")

            # 2단계: ChromaDB 존재 여부로 분류
            certs_to_sync_only, certs_truly_missing = self._classify_by_chroma_status(
                vector_store, certs_without_vector_id
            )

            # 3단계: ChromaDB에 있는 것은 vector_id만 동기화
            synced_from_chroma = self._sync_existing_from_chroma(
                vector_store, certs_to_sync_only
            )

            # 4단계: 고아 레코드 찾기
            orphan_certs, already_synced = self._find_orphan_certs(
                vector_store, certs_with_vector_id
            )

            # 5단계: 처리 대상 결정
            certificates = certs_truly_missing + orphan_certs

            if not certificates:
                total_synced = already_synced + synced_from_chroma
                logger.info(
                    f"모든 자격증이 이미 동기화됨 "
                    f"(기존 {already_synced}개 + 신규 {synced_from_chroma}개)"
                )
                return EmbeddingResult(
                    processed=0,
                    uploaded=0,
                    synced=0,
                    skipped=total_synced,
                    synced_from_chroma=synced_from_chroma,
                    failed_ids=[],
                    skipped_step=False,
                )

            # 6단계: 배치 임베딩 생성 및 업로드
            total_uploaded, total_synced, failed_ids = self._process_embedding_batches(
                vector_store, certificates, certs_truly_missing, orphan_certs
            )

            # 실패 레코드 저장
            if failed_ids:
                failed_certs = [c for c in certificates if c["id"] in failed_ids]
                save_failed_records(
                    "embedding",
                    failed_certs,
                    {c["id"]: "Embedding/Upload failed" for c in failed_certs},
                )

            logger.info(
                f"임베딩 완료: 업로드 {total_uploaded}개, 동기화 {total_synced}개, "
                f"기존 {already_synced}개, ChromaDB 복구 {synced_from_chroma}개"
            )

            return EmbeddingResult(
                processed=len(certificates),
                uploaded=total_uploaded,
                synced=total_synced,
                skipped=already_synced,
                synced_from_chroma=synced_from_chroma,
                failed_ids=failed_ids,
                skipped_step=False,
            )

        finally:
            session.close()

    # --------------------------------------------------------
    # 특정 자격증 재생성
    # --------------------------------------------------------

    async def recreate_certificate(self, cert_id: str) -> dict:
        """특정 자격증의 보강 데이터를 완전히 새로 생성한다.

        기존 보강 데이터(overview, key_points 등)와 벡터를 삭제하고
        웹 검색 + LLM으로 새로 보강 후 임베딩을 생성한다.

        Args:
            cert_id: 자격증 UUID.

        Returns:
            처리 결과 딕셔너리.
        """
        from app.services.embedding.service import EmbeddingService
        from app.services.embedding.vector_store import VectorStoreService

        logger.info("=" * 70)
        logger.info(f"[RECREATE] 자격증 재생성: {cert_id}")
        logger.info("=" * 70)

        session = get_mariadb_session()

        try:
            # 1단계: 자격증 조회
            cert = session.query(Certificate).filter(Certificate.id == cert_id).first()

            if not cert:
                logger.error(f"자격증을 찾을 수 없습니다: {cert_id}")
                return {
                    "status": "error",
                    "message": f"Certificate not found: {cert_id}",
                }

            logger.info(f"  자격증 발견: {cert.title}")

            # 2단계: ChromaDB에서 기존 벡터 삭제
            if cert.vector_id:
                logger.info(f"  기존 벡터 삭제: {cert.vector_id}")
                try:
                    embedding_service = EmbeddingService()
                    vector_store = VectorStoreService(
                        session=session,
                        embedding_service=embedding_service,
                        collection_name=self._collection_name,
                    )
                    # cert_id를 사용하여 삭제 (ChromaDB에서 id로 저장됨)
                    vector_store.delete_certificate(cert.id)
                    logger.info("  ChromaDB 벡터 삭제 완료")
                except Exception as e:
                    logger.warning(f"  ChromaDB 벡터 삭제 실패 (무시): {e}")

            # 3단계: 기존 보강 데이터 클리어
            logger.info("  기존 보강 데이터 클리어...")
            cert.overview = None
            cert.key_points = None
            cert.difficulty_info = None
            cert.cost_info = None
            cert.job_prospects = None
            cert.similar_certificates = None
            cert.latest_trends = None
            cert.free_resources = None
            cert.official_resources = None
            cert.vector_id = None
            session.commit()
            logger.info("  보강 데이터 클리어 완료")

            # 4단계: 보강 실행
            enrich_result = await self.enrich_step(cert_ids=[cert_id])

            if enrich_result["failed"] > 0:
                return {
                    "status": "error",
                    "message": "Enrichment failed",
                    "enrich": enrich_result,
                    "cleared": True,
                }

            # 5단계: 임베딩 실행
            embedding_result = await self.embedding_step(cert_ids=[cert_id])

            logger.info("=" * 70)
            logger.info("[RECREATE] 재생성 완료")
            logger.info("=" * 70)
            logger.info(f"  보강: {'성공' if enrich_result['success'] > 0 else '실패'}")
            logger.info(
                f"  임베딩: {'성공' if embedding_result['uploaded'] > 0 else '실패'}"
            )

            return {
                "status": "success",
                "message": f"Certificate {cert.title} recreated successfully",
                "cert_id": cert_id,
                "cleared": True,
                "enrich": enrich_result,
                "embedding": embedding_result,
            }

        except Exception as e:
            logger.exception(f"재생성 중 오류 발생: {e}")
            return {
                "status": "error",
                "message": str(e),
            }
        finally:
            session.close()

    async def recreate_certificate_by_name(self, name: str) -> dict:
        """자격증 이름으로 검색하여 재생성한다.

        Args:
            name: 자격증 이름 (부분 일치 검색).

        Returns:
            처리 결과 딕셔너리.
        """
        logger.info("=" * 70)
        logger.info(f"[RECREATE] 자격증 검색: {name}")
        logger.info("=" * 70)

        session = get_mariadb_session()

        try:
            # 이름으로 검색 (LIKE)
            cert = (
                session.query(Certificate)
                .filter(Certificate.title.like(f"%{name}%"))
                .first()
            )

            if not cert:
                logger.error(f"자격증을 찾을 수 없습니다: {name}")
                return {
                    "status": "error",
                    "message": f"Certificate not found with name: {name}",
                }

            logger.info(f"  자격증 발견: {cert.title} (ID: {cert.id})")
            session.close()

            # ID로 재생성 실행
            return await self.recreate_certificate(cert.id)

        except Exception as e:
            logger.exception(f"검색 중 오류 발생: {e}")
            session.close()
            return {
                "status": "error",
                "message": str(e),
            }

    # --------------------------------------------------------
    # 파이프라인 실행
    # --------------------------------------------------------

    async def run(
        self,
        test_mode: bool = False,
        limit: Optional[int] = None,
        skip_enrich: bool = False,
        skip_embedding: bool = False,
        skip_existing: bool = False,
        retry_mode: bool = False,
        cert_ids: Optional[list[str]] = None,
    ) -> PipelineResult:
        """파이프라인 전체 실행.

        Args:
            test_mode: True면 limit=1로 설정.
            limit: 처리할 최대 자격증 수.
            skip_enrich: True면 보강 단계 건너뛰기.
            skip_embedding: True면 임베딩 단계 건너뛰기.
            skip_existing: True면 이미 임베딩된 자격증 건너뛰기.
            retry_mode: True면 실패한 자격증 재시도.
            cert_ids: 특정 자격증 ID 목록 (--id 옵션).

        Returns:
            각 단계별 처리 결과.
        """
        logger.info("=" * 70)
        logger.info("데이터 파이프라인 시작")
        logger.info("=" * 70)

        # test_mode면 limit=1
        if test_mode:
            limit = 1

        # 재시도 모드: 실패 레코드 로드
        retry_enrich_ids: Optional[list[str]] = None
        retry_embedding_ids: Optional[list[str]] = None

        if retry_mode:
            enrich_failed = load_latest_failed_records("enrich")
            if enrich_failed:
                retry_enrich_ids = [c["id"] for c in enrich_failed["certificates"]]
                logger.info(f"보강 재시도 대상: {len(retry_enrich_ids)}개")

            embedding_failed = load_latest_failed_records("embedding")
            if embedding_failed:
                retry_embedding_ids = [
                    c["id"] for c in embedding_failed["certificates"]
                ]
                logger.info(f"임베딩 재시도 대상: {len(retry_embedding_ids)}개")

            if not retry_enrich_ids and not retry_embedding_ids:
                logger.info("재시도할 실패 레코드가 없습니다.")
                return PipelineResult(
                    enrich=EnrichResult(
                        processed=0,
                        success=0,
                        failed=0,
                        failed_ids=[],
                        skipped=True,
                    ),
                    embedding=EmbeddingResult(
                        processed=0,
                        uploaded=0,
                        synced=0,
                        skipped=0,
                        synced_from_chroma=0,
                        failed_ids=[],
                        skipped_step=True,
                    ),
                )

        result: PipelineResult = {
            "enrich": EnrichResult(
                processed=0,
                success=0,
                failed=0,
                failed_ids=[],
                skipped=True,
            ),
            "embedding": EmbeddingResult(
                processed=0,
                uploaded=0,
                synced=0,
                skipped=0,
                synced_from_chroma=0,
                failed_ids=[],
                skipped_step=True,
            ),
        }

        # Step 1: Enrich
        if skip_enrich and not retry_enrich_ids and not cert_ids:
            logger.info("[SKIP] 보강 단계 건너뛰기")
        else:
            # cert_ids가 주어지면 해당 ID만 처리
            enrich_ids = (
                cert_ids if cert_ids else (retry_enrich_ids if retry_mode else None)
            )
            enrich_limit = None if (retry_mode or cert_ids) else limit
            result["enrich"] = await self.enrich_step(
                limit=enrich_limit, cert_ids=enrich_ids
            )

        # Step 2: Embedding
        if skip_embedding and not retry_embedding_ids and not cert_ids:
            logger.info("[SKIP] 임베딩 단계 건너뛰기")
        else:
            # cert_ids가 주어지면 해당 ID만 처리
            embedding_ids = (
                cert_ids if cert_ids else (retry_embedding_ids if retry_mode else None)
            )
            embedding_limit = None if (retry_mode or cert_ids) else limit
            result["embedding"] = await self.embedding_step(
                limit=embedding_limit,
                skip_existing=skip_existing,
                cert_ids=embedding_ids,
            )

        # 요약
        logger.info("=" * 70)
        logger.info("파이프라인 완료")
        logger.info("=" * 70)

        if not result["enrich"].get("skipped"):
            logger.info(
                f"  보강: {result['enrich'].get('success', 0)}개 성공, "
                f"{result['enrich'].get('failed', 0)}개 실패"
            )

        if not result["embedding"].get("skipped_step"):
            emb = result["embedding"]
            logger.info(
                f"  임베딩: 업로드 {emb.get('uploaded', 0)}개, "
                f"동기화 {emb.get('synced', 0)}개, 기존 {emb.get('skipped', 0)}개"
            )

        return result


# ============================================================
# 메인 함수
# ============================================================


async def main():
    """메인 엔트리 포인트."""
    parser = argparse.ArgumentParser(
        description="자격증 보강 + 임베딩 생성 통합 파이프라인",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # 테스트 (1개만 처리)
  uv run python -m scripts.data_pipeline --test

  # 특정 개수만 처리
  uv run python -m scripts.data_pipeline --limit 10
        """,
    )

    # 처리 범위 옵션
    parser.add_argument(
        "--test", action="store_true", help="테스트 모드: 1개 자격증만 처리"
    )
    parser.add_argument("--limit", type=int, help="처리할 자격증 최대 개수")
    parser.add_argument("--all", action="store_true", help="모든 미보강 자격증 처리")
    parser.add_argument("--retry", action="store_true", help="실패한 자격증 재시도")
    parser.add_argument(
        "--id",
        type=str,
        nargs="+",
        metavar="CERT_ID",
        help="특정 자격증 ID(들)에 대해 보강+임베딩 실행 (공백으로 구분)",
    )
    parser.add_argument(
        "--recreate",
        type=str,
        metavar="CERT_ID",
        help="특정 자격증 ID의 보강 데이터를 완전히 새로 생성",
    )
    parser.add_argument(
        "--recreate-by-name",
        type=str,
        metavar="NAME",
        help="자격증 이름으로 검색하여 보강 데이터를 완전히 새로 생성",
    )

    # 단계 건너뛰기 옵션
    parser.add_argument("--skip-enrich", action="store_true", help="보강 단계 건너뛰기")
    parser.add_argument(
        "--skip-embedding", action="store_true", help="임베딩 단계 건너뛰기"
    )
    parser.add_argument(
        "--skip-existing", action="store_true", help="이미 임베딩된 자격증 건너뛰기"
    )

    # 기타 옵션
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그 출력")

    args = parser.parse_args()

    # 로깅 설정
    setup_logging(verbose=args.verbose)

    # 인자 검증
    if not (
        args.test
        or args.limit
        or args.all
        or args.retry
        or args.recreate
        or args.recreate_by_name
        or args.id
    ):
        parser.print_help()
        logger.error(
            "\n--test, --limit N, --all, --retry, --id, --recreate 또는 --recreate-by-name 옵션을 지정하세요."
        )
        return

    pipeline = DataPipeline(
        test_mode=args.test,
    )

    try:
        # --recreate 또는 --recreate-by-name 처리
        if args.recreate:
            result = await pipeline.recreate_certificate(args.recreate)
            if result["status"] == "error":
                logger.error(f"재생성 실패: {result['message']}")
                sys.exit(1)
            return

        if args.recreate_by_name:
            result = await pipeline.recreate_certificate_by_name(args.recreate_by_name)
            if result["status"] == "error":
                logger.error(f"재생성 실패: {result['message']}")
                sys.exit(1)
            return

        # 기존 파이프라인 실행
        await pipeline.run(
            test_mode=args.test,
            limit=args.limit if not args.all else None,
            skip_enrich=args.skip_enrich,
            skip_embedding=args.skip_embedding,
            skip_existing=args.skip_existing,
            retry_mode=args.retry,
            cert_ids=args.id,  # --id 옵션
        )
    except KeyboardInterrupt:
        logger.warning("사용자가 작업을 중단했습니다.")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"파이프라인 실행 중 오류 발생: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
