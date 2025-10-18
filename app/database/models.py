from __future__ import annotations
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, DateTime, ForeignKey,
    UniqueConstraint, func
)
from sqlalchemy.orm import relationship, Session, declared_attr

from .db import Base



class BaseModel(Base):
    __abstract__ = True

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    def save(self, db: Session):
        db.add(self)
        db.commit()
        db.refresh(self)
        return self



class FlowMin(BaseModel):
    """
    Basic metadata for a captured flow.
    """
    __tablename__ = "flows_min"

    flow_id = Column(String, primary_key=True)
    extracted_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # One-to-one relationship
    stats = relationship(
        "FlowStats",
        back_populates="flow",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class FlowStats(BaseModel):
    """
    Per-flow 17 statistical features + one-to-one prediction.
    """
    __tablename__ = "flow_stats"

    flow_id = Column(
        String,
        ForeignKey("flows_min.flow_id", ondelete="CASCADE"),
        primary_key=True,
    )

    # --- 17 core statistical features ---
    duration = Column(Float)
    flowBytesPerSecond = Column(Float)
    flowPktsPerSecond = Column(Float)

    max_active = Column(Float)
    max_biat = Column(Float)
    max_fiat = Column(Float)
    max_flowiat = Column(Float)

    mean_biat = Column(Float)
    mean_fiat = Column(Float)
    mean_flowiat = Column(Float)

    min_biat = Column(Float)
    min_fiat = Column(Float)
    min_flowiat = Column(Float)

    std_active = Column(Float)
    std_flowiat = Column(Float)
    total_biat = Column(Float)
    total_fiat = Column(Float)

    # One-to-one relationship with prediction
    prediction = relationship(
        "PredictionResult",
        back_populates="flow",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    flow = relationship("FlowMin", back_populates="stats", passive_deletes=True)



class PredictionResult(BaseModel):
    """
    Single prediction for a flow (one-to-one).
    """
    __tablename__ = "prediction_results"

    id = Column(Integer, primary_key=True, autoincrement=True)

    flow_id = Column(
        String,
        ForeignKey("flow_stats.flow_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    predicted_class = Column(String, nullable=False)  # e.g., "VOIP", "CHAT"
    action = Column(Integer, nullable=False)           # 0=Classify, 1=Route

    # Confidence diagnostics
    max_p = Column(Float, nullable=False)
    margin = Column(Float, nullable=False)
    entropy = Column(Float, nullable=False)

    model_version = Column(String, nullable=True)
    manifest_path = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    flow = relationship("FlowStats", back_populates="prediction", passive_deletes=True)
