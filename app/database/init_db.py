from __future__ import annotations

from sqlalchemy import text
from app.database.db import engine, Base
from app.database.models import *  # noqa: F401

def ensure_schema() -> None:

    with engine.begin() as conn:
        # Drop all tables (CASCADE ensures FK dependencies are removed)
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.commit()  # optional, ensure schema recreated

    # Now recreate all tables defined in SQLAlchemy models
    Base.metadata.create_all(bind=engine)
    print("[init_db] Database schema reset and recreated successfully.")
