"""Dependency injection utilities for API endpoints.

This module provides common dependencies used across API endpoints.
MariaDB (SQLAlchemy) + 임시 Mock 인증으로 변경됨.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

# Type aliases for cleaner dependency injection
DBSession = Annotated[Session, Depends(get_db)]


# 인증 임시 비활성화 (나중에 별도 구현)
class MockUser:
    """임시 사용자 객체 (인증 비활성화 상태)."""

    def __init__(self):
        self.id = "mock-user-id-00000000"
        self.email = "mock@example.com"


async def get_current_user_mock() -> MockUser:
    """임시 인증 (항상 MockUser 반환)."""
    return MockUser()


async def get_current_user_optional_mock() -> MockUser | None:
    """임시 선택적 인증 (항상 MockUser 반환)."""
    return MockUser()


CurrentUser = Annotated[MockUser, Depends(get_current_user_mock)]
OptionalUser = Annotated[MockUser | None, Depends(get_current_user_optional_mock)]

# 레거시 호환용 (이전 코드와의 호환성)
SupabaseDep = DBSession
