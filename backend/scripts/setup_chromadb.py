"""ChromaDB 컬렉션 초기화 스크립트.

외부 ChromaDB 서버에 컬렉션을 생성하고 초기화합니다.

사용법:
    # 컬렉션 생성 (이미 존재하면 무시)
    uv run python -m scripts.setup_chromadb

    # 컬렉션 리셋 (삭제 후 재생성)
    uv run python -m scripts.setup_chromadb --reset

    # 컬렉션 상태 확인
    uv run python -m scripts.setup_chromadb --status
"""

import argparse
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import chromadb

from app.core.config import get_settings


def get_client() -> chromadb.HttpClient:
    """ChromaDB HttpClient를 생성합니다."""
    settings = get_settings()
    return chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)


def setup_collection(reset: bool = False):
    """ChromaDB 컬렉션을 설정합니다.

    Args:
        reset: True면 기존 컬렉션 삭제 후 재생성.
    """
    settings = get_settings()
    collection_name = settings.CHROMA_COLLECTION_NAME

    print("=" * 60)
    print("ChromaDB 컬렉션 설정")
    print("=" * 60)
    print(f"서버: {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
    print(f"컬렉션: {collection_name}")
    print()

    try:
        client = get_client()
        print("[1/3] ChromaDB 서버 연결 성공")

        # 리셋 모드: 기존 컬렉션 삭제
        if reset:
            print("[2/3] 기존 컬렉션 삭제 중...")
            try:
                client.delete_collection(name=collection_name)
                print(f"  [OK] 컬렉션 '{collection_name}' 삭제 완료")
            except Exception as e:
                print(f"  [INFO] 컬렉션이 존재하지 않음: {e}")

        # 컬렉션 생성
        print("[3/3] 컬렉션 생성 중...")
        collection = client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

        # 컬렉션 정보 출력
        count = collection.count()
        print(f"  [OK] 컬렉션 '{collection_name}' 준비 완료")
        print(f"  [INFO] 현재 벡터 수: {count}")

        print()
        print("=" * 60)
        print("설정 완료!")
        print("=" * 60)

    except Exception as e:
        print(f"[ERROR] ChromaDB 연결 실패: {e}")
        print()
        print("다음 사항을 확인하세요:")
        print(
            f"  1. ChromaDB 서버가 {settings.CHROMA_HOST}:{settings.CHROMA_PORT}에서 실행 중인지"
        )
        print("  2. 네트워크 연결이 정상인지")
        print("  3. 방화벽 설정이 올바른지")
        sys.exit(1)


def show_status():
    """ChromaDB 컬렉션 상태를 출력합니다."""
    settings = get_settings()
    collection_name = settings.CHROMA_COLLECTION_NAME

    print("=" * 60)
    print("ChromaDB 상태 확인")
    print("=" * 60)
    print(f"서버: {settings.CHROMA_HOST}:{settings.CHROMA_PORT}")
    print()

    try:
        client = get_client()
        print("[OK] ChromaDB 서버 연결 성공")
        print()

        # 모든 컬렉션 목록
        collections = client.list_collections()
        print(f"총 컬렉션 수: {len(collections)}")
        print()

        for coll in collections:
            count = coll.count()
            print(f"  - {coll.name}: {count}개 벡터")
            if coll.metadata:
                print(f"    메타데이터: {coll.metadata}")

        # 대상 컬렉션 상세 정보
        print()
        print(f"대상 컬렉션: {collection_name}")
        try:
            collection = client.get_collection(name=collection_name)
            count = collection.count()
            print("  [OK] 컬렉션 존재함")
            print(f"  벡터 수: {count}")

            # 샘플 데이터 확인
            if count > 0:
                sample = collection.peek(limit=3)
                print(f"  샘플 ID: {sample['ids'][:3]}")
        except Exception:
            print("  [INFO] 컬렉션이 존재하지 않음")

    except Exception as e:
        print(f"[ERROR] ChromaDB 연결 실패: {e}")
        sys.exit(1)


def main():
    """메인 진입점."""
    parser = argparse.ArgumentParser(description="ChromaDB 컬렉션 초기화 및 관리")
    parser.add_argument(
        "--reset", action="store_true", help="기존 컬렉션 삭제 후 재생성"
    )
    parser.add_argument("--status", action="store_true", help="컬렉션 상태 확인")

    args = parser.parse_args()

    if args.status:
        show_status()
    else:
        setup_collection(reset=args.reset)


if __name__ == "__main__":
    main()
