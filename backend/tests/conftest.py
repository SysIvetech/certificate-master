"""Pytest configuration and fixtures for testing.

This module provides shared fixtures for all tests.
MariaDB (SQLAlchemy) 기반으로 마이그레이션됨.
"""

import uuid
from pathlib import Path
from typing import Generator

import pytest
from dotenv import load_dotenv

# pytest-asyncio 설정: auto 모드로 모든 async 테스트 자동 처리
pytest_plugins = ("pytest_asyncio",)
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_engine
from app.main import app
from app.models.certificate import Certificate as CertificateModel

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


@pytest.fixture(scope="session")
def test_db_engine():
    """Get SQLAlchemy engine for testing."""
    return get_engine()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Get SQLAlchemy session for testing.

    Uses the same database as the main app.
    """
    from sqlalchemy.orm import sessionmaker

    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """Get FastAPI test client.

    This client can make requests to the API without running a server.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def sample_certificate_data() -> dict:
    """Sample certificate data for testing."""
    return {
        "categories": [{"code": "T", "name": "국가기술자격"}],
        "series": "정보처리",
        "title": "정보처리기사",
        "raw_id": "T_정보처리기사",
    }


@pytest.fixture(scope="function")
def sample_study_plan_data() -> dict:
    """Sample study plan data for testing."""
    return {
        "target_date": "2026-06-30",
        "daily_study_hours": 3.0,
        "milestones": [
            {
                "week": 1,
                "title": "기초 이론",
                "description": "프로그래밍 기초 학습",
                "hours": 21,
                "completed": False,
            }
        ],
    }


@pytest.fixture(scope="function")
def sample_checkin_data() -> dict:
    """Sample checkin data for testing."""
    return {"hours_studied": 2.5, "notes": "오늘은 데이터베이스 공부", "mood": "good"}


@pytest.fixture(scope="function")
def clean_test_certificates(test_db_session: Session):
    """Clean up test certificates after each test.

    This fixture runs after the test and removes any certificates
    with raw_id starting with 'TEST_'.
    """
    yield

    # Cleanup after test
    try:
        test_db_session.query(CertificateModel).filter(
            CertificateModel.raw_id.like("TEST_%")
        ).delete(synchronize_session="fetch")
        test_db_session.commit()
    except Exception as e:
        print(f"Cleanup warning: {e}")
        test_db_session.rollback()


@pytest.fixture(scope="function")
def mock_user_token() -> str:
    """Mock JWT token for testing authenticated endpoints.

    In a real scenario, you would create a test user and get a real token.
    For now, this is a placeholder.
    """
    # TODO: Implement real test user creation and token generation
    return "mock_token_for_testing"


@pytest.fixture(scope="function")
def mock_user():
    """Create a mock authenticated user for testing.

    Returns:
        MockUser instance with test data.
    """
    from app.api.deps import MockUser

    return MockUser()


@pytest.fixture(scope="function")
def authenticated_client(mock_user):
    """Get FastAPI test client with mocked authentication.

    This client bypasses authentication for testing.
    """
    from app.core.security import get_current_user
    from app.main import app

    # Override the authentication dependency
    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    # Clean up: remove the override
    app.dependency_overrides.clear()


# Legacy fixture for backward compatibility
@pytest.fixture(scope="session")
def test_supabase_client(test_db_engine):
    """Legacy: Now returns SQLAlchemy session wrapper for compatibility.

    This is kept for backward compatibility with existing tests.
    Tests should migrate to use test_db_session instead.
    """

    class SupabaseCompatWrapper:
        """Wrapper to provide Supabase-like interface for SQLAlchemy."""

        def __init__(self, engine):
            self.engine = engine

        def table(self, name: str):
            return TableWrapper(self.engine, name)

    class TableWrapper:
        def __init__(self, engine, table_name):
            self.engine = engine
            self.table_name = table_name
            self._filters = []
            self._limit = None
            self._select_cols = "*"

        def select(self, cols):
            self._select_cols = cols
            return self

        def eq(self, col, val):
            self._filters.append((col, val))
            return self

        def limit(self, n):
            self._limit = n
            return self

        def execute(self):
            from sqlalchemy.orm import sessionmaker

            SessionLocal = sessionmaker(bind=self.engine)
            session = SessionLocal()
            try:
                if self.table_name == "certificates":
                    query = session.query(CertificateModel)
                    for col, val in self._filters:
                        query = query.filter(getattr(CertificateModel, col) == val)
                    if self._limit:
                        query = query.limit(self._limit)
                    results = query.all()
                    return type(
                        "Response",
                        (),
                        {"data": [r.to_dict() for r in results]},
                    )()
                return type("Response", (), {"data": []})()
            finally:
                session.close()

        def insert(self, data):
            return InsertWrapper(self.engine, self.table_name, data)

    class InsertWrapper:
        def __init__(self, engine, table_name, data):
            self.engine = engine
            self.table_name = table_name
            self.data = data

        def execute(self):
            from sqlalchemy.orm import sessionmaker

            SessionLocal = sessionmaker(bind=self.engine)
            session = SessionLocal()
            try:
                if self.table_name == "certificates":
                    cert = CertificateModel(
                        id=str(uuid.uuid4()),
                        **self.data,
                    )
                    session.add(cert)
                    session.commit()
                    session.refresh(cert)
                    return type(
                        "Response",
                        (),
                        {"data": [cert.to_dict()]},
                    )()
                return type("Response", (), {"data": []})()
            finally:
                session.close()

    return SupabaseCompatWrapper(test_db_engine)
