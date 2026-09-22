"""Dependency injection utilities for API endpoints.

- DB: MariaDB (SQLAlchemy)
- 인증: ivetech auth-service JWT 검증 (app.core.security)
  AUTH_ENABLED=False 이면 모든 요청을 MockUser 로 처리합니다.
"""

from typing import Annotated, Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    AuthenticatedUser,
    MockUser,
    get_current_user,
    get_current_user_optional,
)

# Type aliases for cleaner dependency injection
DBSession = Annotated[Session, Depends(get_db)]

CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
OptionalUser = Annotated[
    Optional[AuthenticatedUser], Depends(get_current_user_optional)
]

__all__ = [
    "DBSession",
    "CurrentUser",
    "OptionalUser",
    "AuthenticatedUser",
    "MockUser",
    "get_current_user",
    "get_current_user_optional",
]
