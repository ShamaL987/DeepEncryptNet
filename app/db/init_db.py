from __future__ import annotations

from .db import engine, Base
from . import models


def ensure_schema() -> None:
    """Create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
