"""Shared pytest fixtures.

Strategy: Use a real PostgreSQL test database (wiped between tests) instead
of mocking SQLAlchemy. This tests real SQL behavior — FK constraints,
ON DELETE CASCADE, enum constraints — that SQLite or mocks would hide.
"""
import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Force test env BEFORE importing app code
os.environ["APP_ENV"] = "test"
os.environ["DEBUG"] = "False"

# We import app modules AFTER setting env, so they pick up test config
from app.database.session import Base, get_db  # noqa: E402
from app.models import *  # noqa: E402, F401, F403  — register all models
from app.models.enums import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from main import app  # noqa: E402


TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://csyrus_user:csyrus_dev_pass@localhost:5432/csyrus_workflow_test",
)


# ---------- Engine + Session factory for tests ----------

engine = create_engine(
    TEST_DATABASE_URL,
    pool_pre_ping=True,
    connect_args={"prepare_threshold": None},  # Disable prepared statements (fixes cached plan error)
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Provide a clean DB session for each test.

    Drops + recreates all tables before each test. Slow but bulletproof.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """TestClient with the DB session overridden to use the test DB."""

    def override_get_db() -> Generator[Session, None, None]:
        try:
            yield db
        finally:
            pass  # session closed by `db` fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------- User factories ----------

@pytest.fixture
def requester(db: Session) -> User:
    """A user with role=Requester."""
    user = User(
        name="Test Requester",
        email="requester@test.com",
        google_id="req-google-1",
        role=UserRole.REQUESTER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def reviewer(db: Session) -> User:
    """A user with role=Reviewer."""
    user = User(
        name="Test Reviewer",
        email="reviewer@test.com",
        google_id="rev-google-1",
        role=UserRole.REVIEWER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def second_requester(db: Session) -> User:
    """A second requester for ownership tests."""
    user = User(
        name="Other Requester",
        email="other@test.com",
        google_id="req-google-2",
        role=UserRole.REQUESTER,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_token(requester: User) -> str:
    """JWT for the requester."""
    return create_access_token(subject=str(requester.id))


@pytest.fixture
def reviewer_token(reviewer: User) -> str:
    """JWT for the reviewer."""
    return create_access_token(subject=str(reviewer.id))


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Auth headers for the requester."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def reviewer_headers(reviewer_token: str) -> dict[str, str]:
    """Auth headers for the reviewer."""
    return {"Authorization": f"Bearer {reviewer_token}"}