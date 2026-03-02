from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.api.core.settings import get_settings


def _build_postgres_dsn() -> str:
    """Build Postgres DSN from env vars.

    Preference order:
    1) POSTGRES_URL if present
    2) Compose from POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_PORT, POSTGRES_DB with host assumed from URL
       (If the platform provides only POSTGRES_URL, that is preferred.)
    """
    s = get_settings()
    if s.postgres_url:
        return s.postgres_url

    # If platform doesn't provide a single URL, we cannot safely guess host.
    # Keeping error explicit to avoid hardcoding.
    raise RuntimeError(
        "Database not configured: set POSTGRES_URL (recommended) "
        "or provide a full connection URL via environment variables."
    )


_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


# PUBLIC_INTERFACE
def get_engine() -> Engine:
    """Return singleton SQLAlchemy Engine."""
    global _engine, _SessionLocal
    if _engine is None:
        dsn = _build_postgres_dsn()
        _engine = create_engine(dsn, pool_pre_ping=True)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


# PUBLIC_INTERFACE
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and ensures it is closed."""
    get_engine()  # ensures sessionmaker exists
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for internal use (non-FastAPI) to get a DB session."""
    get_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
