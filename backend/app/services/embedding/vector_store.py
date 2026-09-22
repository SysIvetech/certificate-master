"""ChromaDB 벡터 스토어 통합.

이 서비스는 의미 기반 유사도 검색을 위해 ChromaDB에서
자격증 임베딩을 관리합니다.

임베딩 서비스는 외부에서 주입 가능합니다 (DI 패턴).
기본값은 OpenAI EmbeddingService입니다.

Supabase에서 MariaDB로 마이그레이션됨 (2026-01-21).
"""

import time
from typing import TYPE_CHECKING, Optional

import chromadb
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_engine
from app.models.certificate import Certificate
from app.services.embedding.service import EmbeddingService

if TYPE_CHECKING:
    from app.services.embedding.protocol import EmbeddingServiceProtocol
from app.utils.certificate_formatter import (
    build_certificate_metadata,
    format_contextual_search_text,
)


def _get_db_session() -> Session:
    """MariaDB 세션을 생성한다."""
    from sqlalchemy.orm import sessionmaker

    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


class VectorStoreService:
    """ChromaDB에서 자격증 임베딩을 관리합니다.

    Attributes:
        NAMESPACE: 자격증 벡터 네임스페이스 (컬렉션 구분용).
        _client: ChromaDB HttpClient 인스턴스.
        _collection: ChromaDB 컬렉션 인스턴스.
        embedding_service: EmbeddingServiceProtocol 구현체 (DI 가능).
        _session: 외부에서 주입된 SQLAlchemy 세션 (선택).
    """

    NAMESPACE = "certificates"

    def __init__(
        self,
        max_retries: int = 3,
        session: Optional[Session] = None,
        embedding_service: Optional["EmbeddingServiceProtocol"] = None,
        collection_name: Optional[str] = None,
    ):
        """벡터 스토어 서비스를 초기화합니다.

        Args:
            max_retries: 연결 실패 시 최대 재시도 횟수 (기본값: 3).
            session: 외부에서 주입할 SQLAlchemy 세션 (선택).
                     주입 시 해당 세션 사용, 미주입 시 내부에서 생성.
            embedding_service: 외부에서 주입할 임베딩 서비스 (선택).
                     주입 시 해당 서비스 사용, 미주입 시 OpenAI EmbeddingService 사용.
            collection_name: 커스텀 컬렉션 이름 (선택).
                     주입 시 해당 이름 사용, 미주입 시 설정값 사용.
                     테스트 환경에서 프로덕션 데이터와 격리하는 데 유용.

        Raises:
            ConnectionError: 최대 재시도 횟수 초과 시.
        """
        settings = get_settings()
        self.host = settings.CHROMA_HOST
        self.port = settings.CHROMA_PORT
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME
        self._session = session  # 외부 주입 세션 저장

        # B2 수정: ChromaDB 연결 재시도 로직
        self._client = chromadb.HttpClient(host=self.host, port=self.port)
        self._connect_with_retry(max_retries)

        self._collection = self._client.get_or_create_collection(
            name=self.collection_name, metadata={"hnsw:space": "cosine"}
        )

        # 임베딩 서비스 주입 (DI 패턴)
        # None이면 기본 OpenAI EmbeddingService 사용
        self.embedding_service = embedding_service or EmbeddingService()

    def _get_session(self) -> tuple[Session, bool]:
        """DB 세션을 반환합니다.

        Returns:
            (session, should_close) 튜플:
            - session: SQLAlchemy 세션
            - should_close: 사용 후 세션을 닫아야 하는지 여부
        """
        if self._session is not None:
            return self._session, False  # 외부 주입 세션은 닫지 않음
        return _get_db_session(), True  # 내부 생성 세션은 닫아야 함

    def _connect_with_retry(self, max_retries: int = 3):
        """ChromaDB 연결을 재시도 로직과 함께 수행합니다.

        지수 백오프 전략을 사용하여 일시적인 연결 실패를 처리합니다.

        Args:
            max_retries: 최대 재시도 횟수.

        Raises:
            ConnectionError: 최대 재시도 횟수 초과 시.
        """
        for attempt in range(max_retries):
            try:
                self._client.heartbeat()  # 연결 테스트
                return  # 성공
            except Exception as e:
                if attempt == max_retries - 1:
                    raise ConnectionError(
                        f"ChromaDB 연결 실패 ({self.host}:{self.port}): {e}"
                    )
                # 지수 백오프: 1초, 2초, 4초...
                wait_time = 2**attempt
                time.sleep(wait_time)

    def upsert_certificate(self, cert_id: str, embedding: list[float], metadata: dict):
        """단일 자격증 임베딩을 upsert합니다.

        Args:
            cert_id: 자격증 고유 ID.
            embedding: 임베딩 벡터.
            metadata: 벡터와 함께 저장할 자격증 메타데이터.
        """
        self._collection.upsert(
            ids=[cert_id], embeddings=[embedding], metadatas=[metadata]
        )

    def upsert_certificates_batch(self, vectors: list[tuple[str, list[float], dict]]):
        """다수의 자격증 임베딩을 upsert합니다.

        Args:
            vectors: (id, embedding, metadata) 튜플 목록.
        """
        if not vectors:
            return

        ids = [v[0] for v in vectors]
        embeddings = [v[1] for v in vectors]
        metadatas = [v[2] for v in vectors]

        self._collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)

    def query_similar(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        filter_dict: Optional[dict] = None,
    ) -> list[dict]:
        """유사한 자격증을 조회합니다.

        Args:
            query_embedding: 쿼리 임베딩 벡터.
            top_k: 반환할 결과 수.
            filter_dict: 선택 메타데이터 필터.

        Returns:
            점수와 메타데이터를 포함한 매칭 결과 목록.
        """
        results = self._collection.query(
            query_embeddings=[query_embedding], n_results=top_k, where=filter_dict
        )

        # ChromaDB는 distance를 반환, score로 변환 (1 - distance for cosine)
        output = []
        if results["ids"] and results["ids"][0]:
            for i, cert_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i]
                score = round(1 - distance, 2)  # cosine distance -> similarity
                output.append(
                    {
                        "id": cert_id,
                        "score": score,
                        "metadata": results["metadatas"][0][i],
                    }
                )

        return output

    def list_vectors(
        self,
        limit: int = 20,
        offset: int = 0,
        include_embeddings: bool = False,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """ChromaDB 컬렉션에서 벡터 목록을 조회합니다.

        Args:
            limit: 조회할 항목 수.
            offset: 건너뛸 항목 수.
            include_embeddings: 임베딩 값을 포함할지 여부.
            where: 선택 필터 조건.

        Returns:
            id, 메타데이터, (옵션) 임베딩을 포함한 벡터 목록.
        """
        includes = ["metadatas"]
        if include_embeddings:
            includes.append("embeddings")

        results = self._collection.get(
            ids=None, where=where, include=includes, limit=limit, offset=offset
        )

        ids = results.get("ids")
        ids = [] if ids is None else ids

        metadatas = results.get("metadatas")
        metadatas = [] if metadatas is None else metadatas

        embeddings = results.get("embeddings")
        embeddings = [] if embeddings is None else embeddings

        vectors = []
        for idx, vector_id in enumerate(ids):
            vector = {
                "id": vector_id,
                "metadata": metadatas[idx] if idx < len(metadatas) else {},
            }

            if include_embeddings:
                vector["values"] = embeddings[idx] if idx < len(embeddings) else None

            vectors.append(vector)

        return vectors

    def get_collection_stats(self) -> dict:
        """컬렉션 통계 정보를 반환합니다."""
        try:
            total_vectors = self._collection.count()
        except Exception:
            total_vectors = 0

        return {
            "host": self.host,
            "port": self.port,
            "collection_name": self.collection_name,
            "total_vectors": total_vectors,
        }

    # ==========================================
    # 텍스트 기반 검색 메서드
    # ==========================================

    def search_records(
        self,
        namespace: str,
        query: str,
        top_k: int = 10,
        filter_dict: Optional[dict] = None,
    ) -> list[dict]:
        """텍스트 기반 검색 (임베딩 사용).

        Args:
            namespace: 네임스페이스 (현재 미사용, 호환성 유지).
            query: 검색 쿼리 텍스트.
            top_k: 반환할 결과 수.
            filter_dict: 선택 메타데이터 필터.

        Returns:
            점수와 메타데이터를 포함한 매칭 결과 목록.
        """
        # 쿼리 텍스트를 임베딩으로 변환
        query_embedding = self.embedding_service.create_embedding(query)

        # 벡터 검색 수행
        return self.query_similar(query_embedding, top_k=top_k, filter_dict=filter_dict)

    def search_by_title(self, query: str, limit: int = 20) -> list[dict]:
        """타이틀 검색 - 의미 기반 검색 사용.

        ChromaDB의 where 필터는 $contains를 지원하지 않으므로,
        의미 기반 검색(semantic search)을 사용하여 타이틀을 검색합니다.

        Args:
            query: 검색 쿼리 텍스트.
            limit: 반환할 결과 수 (기본값: 20).

        Returns:
            id, score, metadata를 포함한 검색 결과 목록.
        """
        # 의미 기반 검색 수행
        results = self.search_records(
            namespace=self.NAMESPACE, query=query, top_k=limit
        )

        # 결과를 list_vectors와 동일한 형식으로 변환
        vectors = []
        for result in results:
            vectors.append(
                {
                    "id": result["id"],
                    "score": result.get("score", 0),
                    "metadata": result.get("metadata", {}),
                }
            )

        return vectors

    def format_record_for_upsert(self, cert: dict) -> dict:
        """자격증 데이터를 upsert용 레코드로 포맷합니다.

        B4 수정: 공통 유틸리티 함수 사용으로 중복 제거.

        Args:
            cert: 자격증 데이터 딕셔너리.

        Returns:
            _id, chunk_text, 메타데이터를 포함한 레코드.
        """
        chunk_text = format_contextual_search_text(cert)
        metadata = build_certificate_metadata(cert)

        return {
            "_id": cert["id"],
            "chunk_text": chunk_text,
            **metadata,
        }

    def check_existing_vectors(self, ids: list[str]) -> list[str]:
        """ChromaDB에 이미 존재하는 벡터 ID를 확인합니다.

        Args:
            ids: 확인할 ID 목록.

        Returns:
            이미 존재하는 ID 목록.
        """
        if not ids:
            return []

        try:
            result = self._collection.get(ids=ids)
            existing_ids = result.get("ids") or []
            return existing_ids
        except Exception:
            # 조회 실패 시 빈 리스트 반환 (모두 새로 생성)
            return []

    def upsert_certificates_batch_integrated(
        self, certs: list[dict], skip_existing: bool = False
    ) -> dict:
        """배치로 자격증을 upsert합니다 (임베딩 포함).

        업로드 후 ChromaDB에서 실제로 저장되었는지 검증합니다.

        Args:
            certs: 자격증 데이터 목록.
            skip_existing: True면 ChromaDB에 이미 존재하는 벡터는 스킵.

        Returns:
            업로드 결과 딕셔너리:
            - uploaded_count: 업로드 시도한 개수
            - verified_count: 검증된 개수
            - skipped_count: 스킵한 개수 (이미 존재)
            - failed_ids: 실패한 ID 목록
            - skipped_ids: 스킵한 ID 목록

        Raises:
            Exception: ChromaDB 연결 실패 또는 업로드 실패 시
        """
        if not certs:
            return {
                "uploaded_count": 0,
                "verified_count": 0,
                "skipped_count": 0,
                "failed_ids": [],
                "skipped_ids": [],
            }

        # 중복 체크 (skip_existing=True인 경우)
        skipped_ids = []
        certs_to_process = certs

        if skip_existing:
            all_ids = [cert["id"] for cert in certs]
            existing_ids = self.check_existing_vectors(all_ids)
            existing_set = set(existing_ids)

            if existing_ids:
                skipped_ids = existing_ids
                certs_to_process = [c for c in certs if c["id"] not in existing_set]
                print(f"      [중복 체크] {len(existing_ids)}개 이미 존재 → 스킵")

        # 처리할 자격증이 없으면 조기 반환
        if not certs_to_process:
            return {
                "uploaded_count": 0,
                "verified_count": 0,
                "skipped_count": len(skipped_ids),
                "failed_ids": [],
                "skipped_ids": skipped_ids,
            }

        records = [self.format_record_for_upsert(cert) for cert in certs_to_process]

        # 텍스트에서 임베딩 생성
        texts = [r["chunk_text"] for r in records]
        embeddings = self.embedding_service.create_embeddings_batch(texts)

        # ChromaDB에 upsert
        ids = [r["_id"] for r in records]
        metadatas = [
            {k: v for k, v in r.items() if k not in ("_id", "chunk_text")}
            for r in records
        ]

        # 업로드 실행 (연결 실패 시 예외 발생)
        self._collection.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas)

        uploaded_count = len(ids)

        # 업로드 후 검증: 실제로 저장되었는지 확인
        verification_result = self._collection.get(ids=ids)
        verified_ids = verification_result.get("ids") or []
        verified_count = len(verified_ids)

        # 실패한 ID 계산
        verified_set = set(verified_ids)
        failed_ids = [id_ for id_ in ids if id_ not in verified_set]

        return {
            "uploaded_count": uploaded_count,
            "verified_count": verified_count,
            "skipped_count": len(skipped_ids),
            "failed_ids": failed_ids,
            "skipped_ids": skipped_ids,
        }

    def get_by_id(self, cert_id: str) -> Optional[dict]:
        """ID로 자격증을 조회합니다.

        Args:
            cert_id: 조회할 자격증 ID.

        Returns:
            id, values(임베딩), metadata를 담은 딕셔너리.
            없으면 None을 반환합니다.
        """
        result = self._collection.get(
            ids=[cert_id], include=["embeddings", "metadatas"]
        )

        ids = result.get("ids") or []
        if not ids:
            return None

        embeddings = result.get("embeddings")
        embeddings = [] if embeddings is None else embeddings
        metadatas = result.get("metadatas")
        metadatas = [] if metadatas is None else metadatas

        values = None
        if len(embeddings) > 0:
            first = embeddings[0]
            values = first.tolist() if hasattr(first, "tolist") else first

        metadata = metadatas[0] if len(metadatas) > 0 else {}
        return {
            "id": ids[0],
            "values": values,
            "metadata": metadata,
        }

    def delete_certificate(self, cert_id: str):
        """단일 자격증을 삭제합니다.

        Args:
            cert_id: 삭제할 자격증 ID.
        """
        self._collection.delete(ids=[cert_id])

    def delete_certificates_batch(self, cert_ids: list[str]):
        """여러 자격증을 삭제합니다.

        Args:
            cert_ids: 삭제할 자격증 ID 목록.
        """
        self._collection.delete(ids=cert_ids)

    def clear_all(self) -> int:
        """컬렉션의 모든 벡터를 삭제합니다.

        컬렉션을 삭제하고 동일한 이름으로 재생성합니다.
        seed_certificates --clear 실행 시 호출됩니다.

        Returns:
            삭제된 벡터 수.
        """
        # 현재 벡터 수 확인
        stats = self.get_collection_stats()
        deleted_count = stats.get("total_vectors", 0)

        # 컬렉션 삭제 후 재생성
        self._client.delete_collection(name=self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name, metadata={"hnsw:space": "cosine"}
        )

        return deleted_count

    # ==========================================
    # DB 동기화 메서드 (vector_id 관리) - MariaDB/SQLAlchemy
    # ==========================================

    def sync_vector_id_to_db(self, cert_id: str, vector_id: str) -> bool:
        """DB에 vector_id를 저장합니다.

        Args:
            cert_id: 자격증 고유 ID.
            vector_id: ChromaDB 벡터 ID.

        Returns:
            성공 여부.
        """
        session, should_close = self._get_session()
        try:
            cert = session.query(Certificate).filter(Certificate.id == cert_id).first()
            if cert:
                cert.vector_id = vector_id
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            if should_close:
                session.close()

    def sync_vector_ids_to_db_batch(self, mappings: list[tuple[str, str]]) -> dict:
        """배치로 여러 자격증의 vector_id를 저장합니다.

        B5 수정: 상세 결과 딕셔너리 반환.

        Args:
            mappings: (cert_id, vector_id) 튜플 목록.

        Returns:
            상세 결과 딕셔너리:
            - success: 성공적으로 업데이트된 개수
            - not_found_ids: DB에서 찾을 수 없는 ID 목록
            - errors: 에러 메시지 목록
        """
        session, should_close = self._get_session()
        success_count = 0
        not_found_ids = []
        errors = []

        try:
            for cert_id, vector_id in mappings:
                cert = (
                    session.query(Certificate).filter(Certificate.id == cert_id).first()
                )
                if cert:
                    cert.vector_id = vector_id
                    success_count += 1
                else:
                    not_found_ids.append(cert_id)

            if not_found_ids:
                print(
                    f"      [경고] DB에서 찾을 수 없는 ID: {not_found_ids[:3]}{'...' if len(not_found_ids) > 3 else ''}"
                )

            session.commit()

            # 커밋 후 검증: 실제로 저장되었는지 확인
            if success_count > 0:
                sample_id = mappings[0][0]
                verify_cert = (
                    session.query(Certificate)
                    .filter(Certificate.id == sample_id)
                    .first()
                )
                if verify_cert and verify_cert.vector_id:
                    pass  # 검증 성공
                else:
                    print("      [경고] 커밋 후 검증 실패: vector_id가 저장되지 않음")

        except Exception as e:
            error_msg = str(e)
            print(f"      [오류] vector_id 동기화 실패: {error_msg}")
            import traceback

            traceback.print_exc()
            session.rollback()
            errors.append(error_msg)
            success_count = 0
        finally:
            if should_close:
                session.close()

        return {
            "success": success_count,
            "not_found_ids": not_found_ids,
            "errors": errors,
        }

    def clear_vector_id_in_db(self, cert_id: str) -> bool:
        """DB에서 vector_id를 초기화합니다.

        Args:
            cert_id: 자격증 고유 ID.

        Returns:
            성공 여부.
        """
        session, should_close = self._get_session()
        try:
            cert = session.query(Certificate).filter(Certificate.id == cert_id).first()
            if cert:
                cert.vector_id = None
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            if should_close:
                session.close()

    def get_certificates_without_vector_id(self) -> list[dict]:
        """vector_id가 없는 (보강된) 자격증을 조회합니다.

        Returns:
            vector_id가 없고 overview가 있는 자격증 목록.
        """
        session, should_close = self._get_session()
        try:
            results = (
                session.query(Certificate)
                .filter(Certificate.vector_id.is_(None))
                .filter(Certificate.overview.isnot(None))
                .all()
            )
            return [cert.to_dict() for cert in results]
        finally:
            if should_close:
                session.close()

    def get_certificates_with_vector_id(self) -> list[dict]:
        """vector_id가 있는 자격증을 조회합니다.

        Returns:
            vector_id가 있는 자격증 목록.
        """
        session, should_close = self._get_session()
        try:
            results = (
                session.query(Certificate)
                .filter(Certificate.vector_id.isnot(None))
                .all()
            )
            return [cert.to_dict() for cert in results]
        finally:
            if should_close:
                session.close()

    def upsert_certificate_with_sync(
        self, cert_id: str, embedding: list[float], metadata: dict
    ):
        """ChromaDB에 업로드하고 DB에 vector_id를 동기화합니다.

        Args:
            cert_id: 자격증 고유 ID (ChromaDB ID로도 사용).
            embedding: 임베딩 벡터.
            metadata: 벡터와 함께 저장할 메타데이터.
        """
        # ChromaDB에 업로드
        self.upsert_certificate(cert_id, embedding, metadata)

        # DB에 vector_id 동기화 (cert_id를 vector_id로 사용)
        self.sync_vector_id_to_db(cert_id, cert_id)

    def delete_certificate_with_sync(self, cert_id: str):
        """ChromaDB에서 삭제하고 DB에서 vector_id를 초기화합니다.

        Args:
            cert_id: 삭제할 자격증 ID.
        """
        # ChromaDB에서 삭제
        self.delete_certificate(cert_id)

        # DB에서 vector_id 초기화
        self.clear_vector_id_in_db(cert_id)

    # ==========================================
    # DB 자격증 데이터 리셋 메서드 (보강 데이터 초기화)
    # ==========================================

    # 리셋 대상 필드 (유지: id, series, title, raw_id, categories)
    RESET_FIELDS = [
        "overview",
        "difficulty",
        "study_period_days",
        "recommended_lectures",
        "exam_info",
        "career_info",
        "user_reviews",
        "official_sources",
        "study_guide",
        "vector_id",
        "passing_rate",
        "job_market_info",
        "cost_breakdown",
        "feasibility_info",
        "exam_schedule_detail",
        "similar_certificates",
    ]

    # 기본값이 0인 필드
    RESET_TO_ZERO_FIELDS = ["view_count"]

    def _reset_certificate_fields(self, cert: Certificate):
        """자격증 객체의 보강 데이터 필드를 리셋합니다.

        Args:
            cert: Certificate 모델 인스턴스.
        """
        for field in self.RESET_FIELDS:
            setattr(cert, field, None)

        for field in self.RESET_TO_ZERO_FIELDS:
            setattr(cert, field, 0)

    def reset_certificate_data_in_db(self, cert_id: str) -> bool:
        """DB에서 자격증의 보강 데이터를 리셋합니다.

        유지 필드: id, series, title, raw_id, categories
        리셋 필드: overview, difficulty, study_period_days, 등

        Args:
            cert_id: 자격증 고유 ID.

        Returns:
            성공 여부.
        """
        session, should_close = self._get_session()
        try:
            cert = session.query(Certificate).filter(Certificate.id == cert_id).first()
            if cert:
                self._reset_certificate_fields(cert)
                session.commit()
                return True
            return False
        except Exception:
            session.rollback()
            return False
        finally:
            if should_close:
                session.close()

    def reset_certificates_data_in_db_batch(self, cert_ids: list[str]) -> dict:
        """배치로 여러 자격증의 보강 데이터를 리셋합니다.

        Args:
            cert_ids: 자격증 ID 목록.

        Returns:
            상세 결과 딕셔너리:
            - success: 성공적으로 리셋된 개수
            - not_found_ids: DB에서 찾을 수 없는 ID 목록
            - errors: 에러 메시지 목록
        """
        session, should_close = self._get_session()
        success_count = 0
        not_found_ids = []
        errors = []

        try:
            for cert_id in cert_ids:
                cert = (
                    session.query(Certificate).filter(Certificate.id == cert_id).first()
                )
                if cert:
                    self._reset_certificate_fields(cert)
                    success_count += 1
                else:
                    not_found_ids.append(cert_id)

            session.commit()

        except Exception as e:
            error_msg = str(e)
            session.rollback()
            errors.append(error_msg)
            success_count = 0
        finally:
            if should_close:
                session.close()

        return {
            "success": success_count,
            "not_found_ids": not_found_ids,
            "errors": errors,
        }

    def delete_certificate_with_reset(self, cert_id: str):
        """ChromaDB에서 삭제하고 DB에서 보강 데이터를 리셋합니다.

        Args:
            cert_id: 삭제할 자격증 ID.
        """
        # ChromaDB에서 삭제
        self.delete_certificate(cert_id)

        # DB에서 보강 데이터 리셋
        self.reset_certificate_data_in_db(cert_id)

    def delete_certificates_batch_with_reset(self, cert_ids: list[str]) -> dict:
        """배치로 ChromaDB에서 삭제하고 DB에서 보강 데이터를 리셋합니다.

        Args:
            cert_ids: 삭제할 자격증 ID 목록.

        Returns:
            상세 결과 딕셔너리.
        """
        # ChromaDB에서 배치 삭제
        self.delete_certificates_batch(cert_ids)

        # DB에서 보강 데이터 배치 리셋
        return self.reset_certificates_data_in_db_batch(cert_ids)
