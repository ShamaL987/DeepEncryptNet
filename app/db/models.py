from __future__ import annotations
from sqlalchemy import Column, String, TIMESTAMP, text, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .db import Base

class FlowMin(Base):
    """
    Minimal record created as soon as a flow CSV is finalized.
    """
    __tablename__ = "flows_min"

    flow_id = Column(String, primary_key=True)
    extracted_at = Column(
        TIMESTAMP(timezone=False), server_default=text("CURRENT_TIMESTAMP"), nullable=False
    )

    # relationship to stats (optional 1-1)
    stats = relationship("FlowStats", back_populates="flow", uselist=False, cascade="all, delete-orphan")


class FlowStats(Base):
    """
    Per-flow statistics computed later from the finalized CSV.
    All columns nullable to allow partial updates.
    """
    __tablename__ = "flow_stats"

    flow_id = Column(String, ForeignKey("flows_min.flow_id", ondelete="CASCADE"), primary_key=True)

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

    flow = relationship("FlowMin", back_populates="stats")
