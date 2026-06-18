"""Script to create all database tables.

Run this once after defining your models. For production, use Alembic
migrations instead — this script is for development convenience.
"""
from app.database.session import Base, engine
# Import models so they register with Base.metadata
from app.models import *  # noqa: F401, F403


def init_db() -> None:
    """Create all tables defined on Base.metadata."""
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Done. Tables created successfully.")


if __name__ == "__main__":
    init_db()