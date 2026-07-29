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
    Build the SQLAlchemy engine, normalising the DATABASE_URL scheme so
    it works with both psycopg2 (legacy) and psycopg3 (psycopg[binary]).

    Neon provides URLs in the form:
        postgresql://user:pass@host/db?sslmode=require
    psycopg3 needs the driver token in the scheme:
        postgresql+psycopg://user:pass@host/db
    We also move sslmode out of the query string into connect_args so that
    psycopg3 receives it in the correct format.
    """
    url = database_url

    # Normalise scheme for psycopg3.
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg://", 1)
    elif url.startswith("postgresql://") and "+psycopg" not in url:
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    # Strip SSL/auth params from URL query string that psycopg3 handles via connect_args.
    # This covers sslmode, channel_binding, and any other Neon-appended params.
    url_clean = re.sub(r"[?&](sslmode|channel_binding)=[^&]*", "", url).rstrip("?")

    is_neon = "neon" in database_url
    connect_args = {"sslmode": "require"} if is_neon else {}

    return create_engine(
        url_clean,
        pool_pre_ping=True,   # rechecks connection health before use → handles Neon idle suspend
        pool_size=3,
        max_overflow=2,
        pool_recycle=300,     # recycle connections every 5 min to avoid stale connections
        connect_args=connect_args,
    )


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """
    FastAPI dependency that yields a DB session.
    Retries up to 3 times with exponential back-off so the first request
    after Neon's compute wakes up does not immediately return a 500.
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
                    "DB connection attempt %d failed (Neon may be waking up): %s",
                    attempt + 1,
                    exc,
                )
                time.sleep(2 ** attempt)  # 1s → 2s → give up
            else:
                raise
    if db is not None:
        try:
            db.close()
        except Exception:
            pass
