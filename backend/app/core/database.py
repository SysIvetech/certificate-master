"""MariaDB 데이터베이스 연결 모듈.

SQLAlchemy를 사용한 MariaDB 연결 관리.
환경 변수를 통해 설정을 관리합니다.
"""

import json
from functools import lru_cache
from typing import Generator
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings


def _json_serializer(obj):
    """한글 등 유니코드를 이스케이프하지 않고 JSON 직렬화."""
    return json.dumps(obj, ensure_ascii=False)


def _json_deserializer(s):
    """JSON 역직렬화."""
    return json.loads(s)


@lru_cache()
def get_mariadb_url() -> str:
    """MariaDB 연결 URL을 생성합니다.

    Returns:
        str: MariaDB 연결 URL
    """
    settings = get_settings()
    return (
        f"mysql+pymysql://{settings.MARIADB_USER}:{quote_plus(settings.MARIADB_PASSWORD)}"
        f"@{settings.MARIADB_HOST}:{settings.MARIADB_PORT}/{settings.MARIADB_DATABASE}"
        f"?charset=utf8mb4"
    )


@lru_cache()
def get_engine():
    """SQLAlchemy 엔진을 생성합니다 (싱글톤).

    Returns:
        Engine: SQLAlchemy 엔진 인스턴스
    """
    return create_engine(
        get_mariadb_url(),
        pool_pre_ping=True,  # 연결 상태 확인
        pool_recycle=3600,  # 1시간마다 연결 재활용
        echo=False,  # SQL 로깅 비활성화
        json_serializer=_json_serializer,  # 한글 유니코드 이스케이프 방지
        json_deserializer=_json_deserializer,
    )


def get_db() -> Generator[Session, None, None]:
    """데이터베이스 세션을 생성합니다 (의존성 주입용).

    Yields:
        Session: SQLAlchemy 세션 인스턴스

    Example:
        ```python
        from fastapi import Depends
        from app.core.database import get_db

        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
        ```
    """
    SessionLocal = sessionmaker(bind=get_engine())
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
