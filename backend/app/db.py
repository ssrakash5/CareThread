from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError, ProgrammingError
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings



def _connect_args() -> dict:
    """For sslmode=verify-full (e.g. CockroachDB Cloud) libpq needs a CA file;
    default to certifi's public bundle unless the URL already names one."""
    url = settings.database_url
    if "sslmode=verify-full" in url and "sslrootcert=" not in url:
        try:
            import certifi
            return {"sslrootcert": certifi.where()}
        except ImportError:
            pass
    return {}


engine = create_engine(settings.database_url, future=True, connect_args=_connect_args())
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def ensure_vector_support() -> None:
    """Enable pgvector on Postgres. CockroachDB has VECTOR built in and does not
    support CREATE EXTENSION, so a failure there is ignored."""
    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        except (ProgrammingError, DBAPIError):
            conn.rollback()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
