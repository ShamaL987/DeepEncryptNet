from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    func,
)
from sqlalchemy.orm import Session, declared_attr
from app.database.db import Base


class BaseModel(Base):
    __abstract__ = True

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    def save(self, db: Session):
        db.add(self)
        db.commit()
        db.refresh(self)
        return self
