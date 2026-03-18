from __future__ import annotations

from sqlalchemy import Column, String, Integer, Float
from sqlalchemy.orm import relationship

from app.database.models.base import BaseModel


class FlowRegistry(BaseModel):
    __tablename__ = "flow_registry"

    flow_id = Column(String, primary_key=True)
    pipeline_name = Column(String, nullable=False, index=True)
    total_packets = Column(Integer, nullable=False)
    total_bytes = Column(Integer, nullable=False)
    prediction = relationship(
        "PredictionResult",
        back_populates="flow_registry",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )