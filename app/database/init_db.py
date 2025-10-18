from __future__ import annotations

from sqlalchemy import text
from .db import engine, Base
from . import models  # noqa: F401  # ensures models are imported for metadata

def ensure_schema() -> None:
    """
    Drop all existing tables and recreate them fresh.

    This guarantees a clean start for each re-run (useful during development).
    """
    with engine.begin() as conn:
        # Drop all tables (CASCADE ensures FK dependencies are removed)
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.commit()  # optional, ensure schema recreated

    # Now recreate all tables defined in SQLAlchemy models
    Base.metadata.create_all(bind=engine)
    print("[init_db] Database schema reset and recreated successfully.")
