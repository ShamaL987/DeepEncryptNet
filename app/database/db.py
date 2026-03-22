from __future__ import annotations
from contextlib import contextmanager
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

from app.settings import get_settings_manager


def _build_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")

    if all([db_host, db_name, db_user, db_password]):
        return str(
            URL.create(
                drivername="postgresql+psycopg2",
                username=db_user,
                password=db_password,
                host=db_host,
                port=int(db_port),
                database=db_name,
            )
        )

    settings = get_settings_manager().get_all()
    db_cfg = settings.get("database", {})

    return str(
        URL.create(
            drivername="postgresql+psycopg2",
            username=db_cfg["user"],
            password=db_cfg["password"],
            host=db_cfg["host"],
            port=int(db_cfg["port"]),
            database=db_cfg["name"],
        )
    )


DATABASE_URL = _build_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()