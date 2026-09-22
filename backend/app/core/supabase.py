"""Supabase client initialization and utilities.

This module provides Supabase client instances for backend services.
Uses singleton pattern for efficient connection management.
"""

from functools import lru_cache

from supabase import Client, create_client

from .config import get_settings


@lru_cache()
def get_supabase_client() -> Client:
    """Get singleton Supabase client for backend services.

    Uses service role key for full database access.
    This client bypasses RLS policies.

    Returns:
        Supabase client instance with service role privileges.
    """
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def get_supabase_anon_client() -> Client:
    """Get Supabase client with anonymous key.

    Uses anon key for client-side-like access.
    This client respects RLS policies.

    Returns:
        Supabase client instance with anonymous privileges.
    """
    settings = get_settings()
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


def get_supabase_user_client(access_token: str) -> Client:
    """Get Supabase client authenticated with user's access token.

    Creates a client that acts on behalf of the authenticated user.
    This client respects RLS policies scoped to the user.

    Args:
        access_token: JWT access token from Supabase Auth.

    Returns:
        Supabase client instance with user's privileges.
    """
    settings = get_settings()
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    # Set the user's session
    client.auth.set_session(access_token, "")
    return client


# Type alias for dependency injection
SupabaseClient = Client
