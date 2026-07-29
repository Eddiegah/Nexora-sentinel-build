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
    Build the SQLAlchemy engine for psycopg3 (psycopg[binary]).
    Works on any Python version including 3.14 — pure binary wheels available.

    Neon URL format:
        postgresql://user:pass@host/db?sslmode=require&channel_binding=require

    psycopg3 needs:
        - scheme: postgresql+psycopg://
        - sslmode in connect_args (not query string)
        - channel_binding stripped
    """
    url = database_url

    # Normalise scheme for psycopg3
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    # Strip params psycopg3 doesn't accept in the URL query string
    url = re.sub(r"[?&](sslmode|channel_binding)=[^&]*", "", url).rstrip("?&")

    is_neon = "neon" in database_url
    connect_args = {"sslmode": "require"} if is_neon else {}

    return create_engine(
        url,
        pool_pre_ping=True,
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
    """FastAPI dependency — yields a DB session with retry for Neon idle reconnects."""
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
                    attempt + 1, exc,
                )
                time.sleep(2 ** attempt)
            else:
                raise
    if db is not None:
        try:
            db.close()
        except Exception:
            pass
