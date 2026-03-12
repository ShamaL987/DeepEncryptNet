from __future__ import annotations

from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime, ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database.models.base import BaseModel


class FlowStats(BaseModel):
    """
    Fully observed and closed network flow.
    Contains all extracted statistical features.
    """

    __tablename__ = "flow_stats"

    flow_id = Column(
        String,
        ForeignKey("flow_registry.flow_id", ondelete="CASCADE"),
        primary_key=True,
    )

    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    duration = Column(Float, nullable=False)

    flowBytesPerSecond = Column(Float, nullable=False)
    flowPktsPerSecond = Column(Float, nullable=False)

    max_active = Column(Float)
    std_active = Column(Float)

    max_biat = Column(Float)
    mean_biat = Column(Float)
    min_biat = Column(Float)
    total_biat = Column(Float)

    max_fiat = Column(Float)
    mean_fiat = Column(Float)
    min_fiat = Column(Float)
    total_fiat = Column(Float)

    max_flowiat = Column(Float)
    mean_flowiat = Column(Float)
    min_flowiat = Column(Float)
    std_flowiat = Column(Float)

    flow_registry = relationship("FlowRegistry")