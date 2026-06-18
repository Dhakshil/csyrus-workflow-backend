from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase

from app.core.config import settings


# The engine manages the connection pool to PostgreSQL.
# pool_pre_ping=True sends a SELECT 1 before reusing a connection
# to detect stale connections (important for long-running apps).
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG,
)

# SessionLocal is a factory: call SessionLocal() to get a new Session.
# autocommit=False means we control transactions explicitly (commit/rollback).
# autoflush=False prevents SQLAlchemy from auto-flushing pending changes
# before queries, which can cause surprising behavior in tests.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Declarative base class for all SQLAlchemy models.

    Every model class inherits from Base. SQLAlchemy tracks them all
    and can create the tables via Base.metadata.create_all(engine).
    """
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session per request.

    Usage in a route:
        @router.get("/items")
        def list_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    The session is closed in the finally block, even if the route
    raises an exception. This prevents connection leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()