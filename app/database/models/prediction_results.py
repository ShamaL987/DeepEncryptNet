from __future__ import annotations

from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    Integer,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy.orm import relationship
from app.database.models.base import BaseModel


class PredictionResult(BaseModel):
    __tablename__ = "prediction_results"

    id = Column(Integer, primary_key=True, autoincrement=True)

    flow_id = Column(
        String,
        ForeignKey("flow_registry.flow_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    predicted_class = Column(String, nullable=False)
    action = Column(Integer, nullable=False)

    pred_idx = Column(Integer, nullable=False, default=-1)

    probs = Column(JSON, nullable=False)
    embedding = Column(JSON, nullable=True)

    max_p = Column(Float, nullable=False)
    margin = Column(Float, nullable=False)
    entropy = Column(Float, nullable=False)

    model_version = Column(String, nullable=True)
    manifest_path = Column(String, nullable=True)

    flow_registry = relationship(
        "FlowRegistry",
        back_populates="prediction",
        passive_deletes=True,
    )