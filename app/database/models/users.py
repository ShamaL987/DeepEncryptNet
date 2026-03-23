from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.sql import func

from app.database.models.base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    username = Column(String, nullable=False, unique=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    password_hash = Column(String, nullable=False)

    api_token_prefix = Column(String, nullable=True, index=True)
    api_token_encrypted = Column(Text, nullable=True)
    api_token_hash = Column(String, nullable=True, unique=True)
    is_token_revoked = Column(Boolean, nullable=False, default=False)
    token_created_at = Column(DateTime(timezone=True), nullable=True)
    token_revoked_at = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

