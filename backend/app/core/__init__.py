"""Core module for Certificate Master backend.

This module contains core utilities including:
- config: Application settings
- database: MariaDB(SQLAlchemy) connection
- security: ivetech auth-service JWT 검증
"""

from .config import Settings, get_settings
from .database import get_db, get_engine
from .security import (
    AuthenticatedUser,
    MockUser,
    get_current_user,
    get_current_user_optional,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    # Database (MariaDB)
    "get_db",
    "get_engine",
    # Security
    "AuthenticatedUser",
    "MockUser",
    "get_current_user",
    "get_current_user_optional",
]
