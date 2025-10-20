from __future__ import annotations
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from app.settings import get_settings

settings = get_settings()
db_cfg = settings.get("database")

DATABASE_URL = (
    f"postgresql+psycopg2://{db_cfg['user']}:{db_cfg['password']}"
    f"@{db_cfg['host']}:{db_cfg['port']}/{db_cfg['name']}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
)
Base = declarative_base()

@contextmanager
def session_scope():
    """Yields a transactional session with commit/rollback."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
