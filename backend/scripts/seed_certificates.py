"""파싱된 자격증 데이터를 MariaDB certificates 테이블에 적재하는 스크립트.

Supabase에서 MariaDB로 마이그레이션됨 (2026-01-21).

사용법:
    uv run python -m scripts.seed_certificates
    uv run python -m scripts.seed_certificates --limit 100  # 100건만 적재
    uv run python -m scripts.seed_certificates --clear      # 기존 데이터 삭제 후 적재
    uv run python -m scripts.seed_certificates --category 국가기술자격  # 특정 카테고리만
    uv run python -m scripts.seed_certificates --file-name national_technical  # 파일 이름으로 적재

카테고리별 파일 이름:
    - national_professional: 국가전문자격
    - national_technical: 국가기술자격
    - course_evaluation: 과정평가형자격
    - work_study: 일학습병행자격
"""

import argparse
import json
import sys
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

# backend 디렉토리를 path에 추가
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import get_engine
from app.models.certificate import Certificate

# 카테고리별 파일 매핑 (한글 카테고리명 -> 영문 파일명)
CATEGORY_FILES: dict[str, str] = {
    "국가전문자격": "national_professional",
    "국가기술자격": "national_technical",
    "과정평가형자격": "course_evaluation",
    "일학습병행자격": "work_study",
}

# 파일명 -> 카테고리명 역매핑
FILE_TO_CATEGORY: dict[str, str] = {v: k for k, v in CATEGORY_FILES.items()}

# 유효한 파일 이름 목록
VALID_FILE_NAMES: list[str] = list(FILE_TO_CATEGORY.keys())


def load_certificates(file_path: Path) -> list[dict]:
    """JSON 파일에서 자격증 데이터를 불러온다."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_file_path_for_category(data_dir: Path, category: str | None) -> Path:
    """카테고리에 따른 파일 경로를 반환한다.

    Args:
        data_dir: 데이터 디렉토리 경로 (backend/data)
        category: 카테고리명 (None이면 기본 파일)

    Returns:
        JSON 파일 경로
    """
    if category is None:
        return data_dir / "processed" / "certificates_parsed.json"

    if category not in CATEGORY_FILES:
        raise ValueError(f"Unknown category: {category}")

    filename = CATEGORY_FILES[category]
    return data_dir / "processed" / "by_category" / f"{filename}.json"


def get_file_path_for_file_name(data_dir: Path, file_name: str) -> Path:
    """파일 이름에 따른 파일 경로를 반환한다.

    Args:
        data_dir: 데이터 디렉토리 경로 (backend/data)
        file_name: 파일 이름 (national_technical, national_professional 등)

    Returns:
        JSON 파일 경로

    Raises:
        ValueError: 알 수 없는 파일 이름인 경우
    """
    if file_name not in VALID_FILE_NAMES:
        raise ValueError(
            f"Unknown file name: {file_name}. "
            f"Valid options: {', '.join(VALID_FILE_NAMES)}"
        )

    return data_dir / "processed" / "by_category" / f"{file_name}.json"


def get_category_for_file_name(file_name: str) -> str:
    """파일 이름에 해당하는 카테고리명을 반환한다.

    Args:
        file_name: 파일 이름 (national_technical 등)

    Returns:
        카테고리명 (국가기술자격 등)
    """
    return FILE_TO_CATEGORY.get(file_name, file_name)


def get_mariadb_session() -> Session:
    """MariaDB 세션을 생성한다."""
    from sqlalchemy.orm import sessionmaker

    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def clear_certificates_mariadb(
    session: Session,
    category_name: str | None = None,
    raw_id_prefix: str | None = None,
) -> int:
    """certificates 테이블의 레코드를 삭제한다.

    Args:
        session: SQLAlchemy 세션
        category_name: 삭제할 카테고리명 (None이면 전체 삭제)
        raw_id_prefix: 삭제할 raw_id 접두어 (테스트용)

    Returns:
        삭제된 레코드 수
    """
    from sqlalchemy import func, text

    query = session.query(Certificate)

    if raw_id_prefix:
        query = query.filter(Certificate.raw_id.like(f"{raw_id_prefix}%"))
    elif category_name:
        # categories JSON 배열에서 name 필드로 검색
        query = query.filter(
            func.json_contains(
                Certificate.categories,
                func.json_quote(category_name),
                text("'$[*].name'"),
            )
        )

    count = query.count()
    query.delete(synchronize_session="fetch")
    session.commit()
    return count


def seed_certificates_mariadb(
    session: Session,
    certificates: list[dict],
    batch_size: int = 100,
) -> tuple[int, int, int, int]:
    """자격증 데이터를 MariaDB에 배치로 삽입한다.

    같은 title의 자격증이 이미 존재하면 categories 목록에 새 카테고리를 추가한다.

    Args:
        session: SQLAlchemy 세션
        certificates: 자격증 데이터 리스트
        batch_size: 배치 크기

    Returns:
        (삽입 건수, 카테고리 추가 건수, 건너뜀 건수, 실패 건수) 튜플
    """
    inserted = 0
    category_added = 0
    skipped = 0
    failed = 0

    total_batches = (len(certificates) + batch_size - 1) // batch_size

    for i in range(0, len(certificates), batch_size):
        batch = certificates[i : i + batch_size]
        batch_num = (i // batch_size) + 1

        try:
            batch_inserted = 0
            batch_category_added = 0
            batch_skipped = 0

            for cert_data in batch:
                title = cert_data["title"]

                # categories 배열 처리 (신규 형식 또는 기존 형식 모두 지원)
                if "categories" in cert_data and cert_data["categories"]:
                    # 신규 형식: categories 배열
                    input_categories = cert_data["categories"]
                else:
                    # 기존 형식: code, category 필드 (하위 호환성)
                    code = cert_data.get("code", "")
                    category_name = cert_data.get("category", "")
                    input_categories = [{"code": code, "name": category_name}]

                # title 기준으로 기존 레코드 확인
                existing = (
                    session.query(Certificate)
                    .filter(Certificate.title == title)
                    .first()
                )

                if existing:
                    # 기존 자격증에 카테고리 추가
                    current_categories = existing.categories or []
                    added_any = False

                    for new_cat in input_categories:
                        code = new_cat.get("code", "")
                        name = new_cat.get("name", "")

                        # 이미 같은 카테고리가 있는지 확인
                        has_category = any(
                            cat.get("code") == code or cat.get("name") == name
                            for cat in current_categories
                        )

                        if not has_category:
                            # 새 카테고리 추가
                            current_categories.append({"code": code, "name": name})
                            added_any = True

                    if added_any:
                        existing.categories = current_categories
                        batch_category_added += 1
                    else:
                        batch_skipped += 1
                else:
                    # 새 자격증 삽입 (categories 배열로 초기화)
                    new_cert = Certificate(
                        id=str(uuid.uuid4()),
                        categories=input_categories,
                        series=cert_data.get("series"),
                        title=title,
                        raw_id=cert_data["raw_id"],
                    )
                    session.add(new_cert)
                    batch_inserted += 1

            session.commit()
            inserted += batch_inserted
            category_added += batch_category_added
            skipped += batch_skipped
            print(
                f"  배치 {batch_num}/{total_batches}: 삽입 {batch_inserted}건, 카테고리 추가 {batch_category_added}건, 건너뜀 {batch_skipped}건"
            )

        except Exception as e:
            session.rollback()
            failed += len(batch)
            print(f"  배치 {batch_num}/{total_batches}: 오류 - {str(e)}")

    return inserted, category_added, skipped, failed


# ===== Legacy Supabase 함수들 (하위 호환성) =====
def get_supabase_client():
    """[Deprecated] Supabase 대신 MariaDB 사용."""
    raise NotImplementedError(
        "Supabase는 더 이상 사용하지 않습니다. get_mariadb_session()을 사용하세요."
    )


def clear_certificates(client, category: str | None = None) -> int:
    """[Deprecated] MariaDB 버전 사용."""
    raise NotImplementedError("clear_certificates_mariadb()를 사용하세요.")


def seed_certificates(client, certificates: list[dict], batch_size: int = 100):
    """[Deprecated] MariaDB 버전 사용."""
    raise NotImplementedError("seed_certificates_mariadb()를 사용하세요.")


def main():
    """Main function to run the seeding script."""
    parser = argparse.ArgumentParser(
        description="자격증 데이터를 MariaDB certificates 테이블에 적재"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="적재할 최대 레코드 수",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="기존 데이터를 삭제 후 적재",
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=list(CATEGORY_FILES.keys()),
        default=None,
        help="특정 카테고리만 적재 (기본: 전체)",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="자격증 JSON 파일 경로 (--category, --file-name과 함께 사용 불가)",
    )
    parser.add_argument(
        "--file-name",
        type=str,
        choices=VALID_FILE_NAMES,
        default=None,
        help="카테고리별 파일 이름 (national_technical, national_professional, course_evaluation, work_study)",
    )

    args = parser.parse_args()

    # --file, --category, --file-name 동시 사용 금지
    options_used = sum([bool(args.file), bool(args.category), bool(args.file_name)])
    if options_used > 1:
        print("[오류] --file, --category, --file-name은 동시에 사용할 수 없습니다.")
        sys.exit(1)

    # 데이터 디렉토리 경로
    data_dir = Path(__file__).parent.parent / "data"

    # 파일 경로 결정 및 카테고리명 설정
    category_name: str | None = None

    if args.file:
        file_path = Path(args.file)
        if not file_path.is_absolute():
            file_path = data_dir / args.file
    elif args.file_name:
        file_path = get_file_path_for_file_name(data_dir, args.file_name)
        category_name = get_category_for_file_name(args.file_name)
    elif args.category:
        file_path = get_file_path_for_category(data_dir, args.category)
        category_name = args.category
    else:
        file_path = get_file_path_for_category(data_dir, None)

    if not file_path.exists():
        print(f"[오류] 파일을 찾을 수 없습니다: {file_path}")
        sys.exit(1)

    # 카테고리 정보 출력
    if args.file_name:
        print(f"파일 이름: {args.file_name}")
        print(f"카테고리: {category_name}")
    elif args.category:
        print(f"카테고리: {args.category}")
    else:
        print("카테고리: 전체")

    print(f"{file_path}에서 자격증 데이터를 불러옵니다...")
    certificates = load_certificates(file_path)
    print(f"{len(certificates)}건 로드 완료")

    if args.limit:
        certificates = certificates[: args.limit]
        print(f"{len(certificates)}건으로 제한합니다")

    print("\nMariaDB에 연결 중...")
    try:
        session = get_mariadb_session()
        print("연결 성공!")
    except Exception as e:
        print(f"[오류] {e}")
        sys.exit(1)

    try:
        if args.clear:
            if category_name:
                print(f"\n'{category_name}' 카테고리 데이터를 삭제합니다...")
            else:
                print("\n기존 certificates 데이터를 삭제합니다...")
            deleted = clear_certificates_mariadb(session, category_name=category_name)
            print(f"  MariaDB: {deleted}건 삭제 완료")

            # 전체 삭제일 때만 벡터 DB도 비움
            if not category_name:
                print("\n벡터 DB(ChromaDB)도 비웁니다...")
                try:
                    from app.services.vector_store import VectorStoreService

                    vector_store = VectorStoreService()
                    vector_deleted = vector_store.clear_all()
                    print(f"  ChromaDB: {vector_deleted}건 삭제 완료")
                except Exception as e:
                    print(f"  ChromaDB 삭제 실패 (무시됨): {e}")

        print(f"\n{len(certificates)}건을 적재합니다...")
        inserted, category_added, skipped, failed = seed_certificates_mariadb(
            session, certificates
        )

        print(f"\n{'='*50}")
        print("적재 완료!")
        if category_name:
            print(f"  카테고리: {category_name}")
        if args.file_name:
            print(f"  파일 이름: {args.file_name}")
        print(f"  삽입: {inserted}")
        print(f"  카테고리 추가: {category_added}")
        print(f"  건너뜀 (이미 존재): {skipped}")
        print(f"  실패: {failed}")
        print(f"{'='*50}")

        if failed > 0:
            sys.exit(1)

    finally:
        session.close()


if __name__ == "__main__":
    main()
