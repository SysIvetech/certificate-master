"""Authentication and security utilities.

This module provides JWT token verification and user authentication
using Supabase Auth.
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client

from .supabase import get_supabase_client

# HTTP Bearer scheme for JWT tokens
security = HTTPBearer()


class AuthenticatedUser:
    """Represents an authenticated user from Supabase Auth.

    Attributes:
        id: User's UUID from Supabase Auth.
        email: User's email address.
        user_metadata: Additional user metadata.
    """

    def __init__(self, user_data: dict):
        """Initialize AuthenticatedUser from Supabase user data.

        Args:
            user_data: Raw user data from Supabase Auth.
        """
        self.id: str = user_data.get("id", "")
        self.email: Optional[str] = user_data.get("email")
        self.user_metadata: dict = user_data.get("user_metadata", {})
        self._raw = user_data

    def __repr__(self) -> str:
        return f"AuthenticatedUser(id={self.id}, email={self.email})"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    supabase: Client = Depends(get_supabase_client),
) -> AuthenticatedUser:
    """Verify JWT token and return authenticated user.

    This dependency extracts the JWT from the Authorization header,
    verifies it with Supabase, and returns the authenticated user.

    Args:
        credentials: HTTP Authorization credentials containing JWT.
        supabase: Supabase client instance.

    Returns:
        AuthenticatedUser instance with user details.

    Raises:
        HTTPException: If token is invalid or user not found.
    """
    try:
        token = credentials.credentials
        # Verify token and get user
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return AuthenticatedUser(user_response.user.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
    supabase: Client = Depends(get_supabase_client),
) -> Optional[AuthenticatedUser]:
    """Optionally get authenticated user if token is provided.

    Unlike get_current_user, this does not raise an error if
    no token is provided. Useful for endpoints that work for
    both authenticated and anonymous users.

    Args:
        credentials: Optional HTTP Authorization credentials.
        supabase: Supabase client instance.

    Returns:
        AuthenticatedUser if token is valid, None otherwise.
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        user_response = supabase.auth.get_user(token)

        if user_response and user_response.user:
            return AuthenticatedUser(user_response.user.model_dump())
        return None

    except Exception:
        return None
