from __future__ import annotations

from sqlalchemy import inspect
from app.database.db import engine, Base
from app.database.models import *  # noqa: F401


PROTECTED_TABLES = {"users"}


def ensure_schema() -> None:
    inspector = inspect(engine)

    existing_table_names = set(inspector.get_table_names())
    tables_to_drop = [
        table
        for table in reversed(Base.metadata.sorted_tables)
        if table.name in existing_table_names and table.name not in PROTECTED_TABLES
    ]

    if tables_to_drop:
        Base.metadata.drop_all(bind=engine, tables=tables_to_drop)

    Base.metadata.create_all(bind=engine)
    print("[init_db] Database schema reset successfully. Protected tables were preserved.")