"""Core module for Certificate Master backend.

This module contains core utilities including:
- config: Application settings
- database: MariaDB(SQLAlchemy) connection
- supabase: Supabase client initialization (Auth용)
- security: Authentication and authorization
"""

from .config import Settings, get_settings
from .database import get_db, get_engine
from .security import AuthenticatedUser, get_current_user, get_current_user_optional
from .supabase import (
    SupabaseClient,
    get_supabase_anon_client,
    get_supabase_client,
    get_supabase_user_client,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    # Database (MariaDB)
    "get_db",
    "get_engine",
    # Supabase (Auth용, DB는 MariaDB 사용)
    "SupabaseClient",
    "get_supabase_client",
    "get_supabase_anon_client",
    "get_supabase_user_client",
    # Security
    "AuthenticatedUser",
    "get_current_user",
    "get_current_user_optional",
]
