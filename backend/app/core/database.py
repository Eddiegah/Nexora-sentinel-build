import re
import time
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.exc import OperationalError
from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def _make_engine(database_url: str):
    """
    Build the SQLAlchemy engine with psycopg2-binary.

    Neon provides URLs like:
        postgresql://user:pass@host/db?sslmode=require&channel_binding=require

    psycopg2 needs:
        - scheme: postgresql:// (already correct — do NOT add +psycopg2 suffix
          because psycopg2-binary registers itself as the default dialect)
        - sslmode kept in the URL query string (psycopg2 reads it there)
        - channel_binding stripped (psycopg2 doesn't support it)
    """
    url = database_url

    # Normalise postgres:// → postgresql:// (Heroku/Neon shorthand)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    # Strip psycopg3-specific params psycopg2 doesn't understand.
    url = re.sub(r"[?&]channel_binding=[^&]*", "", url).rstrip("?&")

    # Neon requires SSL — pass via connect_args for reliability
    is_neon = "neon" in database_url
    connect_args = {"sslmode": "require"} if is_neon else {}

    return create_engine(
        url,
        pool_pre_ping=True,   # catches stale connections → handles Neon idle suspend
        pool_size=3,
        max_overflow=2,
        pool_recycle=300,
        connect_args=connect_args,
    )


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """
    FastAPI dependency — yields a DB session with retry/back-off for
    Neon's brief reconnect delay after compute suspension.
    """
    db = None
    retries = 3
    for attempt in range(retries):
        try:
            db = SessionLocal()
            yield db
            return
        except OperationalError as exc:
            if db is not None:
                try:
                    db.close()
                except Exception:
                    pass
                db = None
            if attempt < retries - 1:
                logger.warning(
                    "DB connection attempt %d failed (Neon may be waking): %s",
                    attempt + 1,
                    exc,
                )
                time.sleep(2 ** attempt)
            else:
                raise
    if db is not None:
        try:
            db.close()
        except Exception:
            pass
