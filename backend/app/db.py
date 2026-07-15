"""Database plumbing: the engine, session factory, and FastAPI dependency.

- `engine` is the connection pool to Postgres (created once, reused).
- `SessionLocal` produces short-lived Session objects (one per request).
- `Base` is the parent class every ORM model inherits from; SQLAlchemy tracks all
  subclasses on it so tools like Alembic can see the full schema.
- `get_db` is a FastAPI dependency that hands a request its own session and makes
  sure the session is closed afterward, even if the request errors.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # transparently recycle stale connections
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped session, guaranteeing it is closed afterward."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
