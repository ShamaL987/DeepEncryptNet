from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.models.base import BaseModel


class HTTPSFlowStats(BaseModel):
    __tablename__ = "https_flow_stats"

    flow_id = Column(
        String,
        ForeignKey("flow_registry.flow_id", ondelete="CASCADE"),
        primary_key=True,
    )

    BYTES = Column(Float, nullable=False, default=0.0)
    BYTES_REV = Column(Float, nullable=False, default=0.0)
    PACKETS = Column(Integer, nullable=False, default=0)
    PACKETS_REV = Column(Integer, nullable=False, default=0)
    BRST_COUNT = Column(Integer, nullable=False, default=0)
    REV_MORE = Column(Float, nullable=False, default=0.0)

    PKT_LENGTHS_MEAN = Column(Float, nullable=False, default=0.0)
    PKT_LENGTHS_MAX = Column(Float, nullable=False, default=0.0)
    PKT_LENGTHS_STD = Column(Float, nullable=False, default=0.0)
    PKT_LENGTHS_25 = Column(Float, nullable=False, default=0.0)
    PKT_LENGTHS_50 = Column(Float, nullable=False, default=0.0)
    PKT_LENGTHS_75 = Column(Float, nullable=False, default=0.0)

    INTERVALS_MEAN = Column(Float, nullable=False, default=0.0)
    INTERVALS_MAX = Column(Float, nullable=False, default=0.0)
    INTERVALS_STD = Column(Float, nullable=False, default=0.0)
    INTERVALS_25 = Column(Float, nullable=False, default=0.0)
    INTERVALS_50 = Column(Float, nullable=False, default=0.0)
    INTERVALS_75 = Column(Float, nullable=False, default=0.0)

    BRST_BYTES_MEAN = Column(Float, nullable=False, default=0.0)
    BRST_BYTES_STD = Column(Float, nullable=False, default=0.0)
    BRST_PACKETS_MEAN = Column(Float, nullable=False, default=0.0)
    BRST_PACKETS_STD = Column(Float, nullable=False, default=0.0)
    BRST_INTERVALS_MEAN = Column(Float, nullable=False, default=0.0)
    BRST_INTERVALS_MAX = Column(Float, nullable=False, default=0.0)
    BRST_INTERVALS_STD = Column(Float, nullable=False, default=0.0)
    BRST_INTERVALS_25 = Column(Float, nullable=False, default=0.0)
    BRST_DURATION_MEAN = Column(Float, nullable=False, default=0.0)
    BRST_DURATION_MAX = Column(Float, nullable=False, default=0.0)
    BRST_DURATION_STD = Column(Float, nullable=False, default=0.0)

    BRST_BYTES_0 = Column(Float, nullable=False, default=0.0)
    BRST_BYTES_1 = Column(Float, nullable=False, default=0.0)
    BRST_BYTES_2 = Column(Float, nullable=False, default=0.0)
    BRST_BYTES_3 = Column(Float, nullable=False, default=0.0)
    BRST_BYTES_4 = Column(Float, nullable=False, default=0.0)
    BRST_BYTES_5 = Column(Float, nullable=False, default=0.0)
    BRST_BYTES_6 = Column(Float, nullable=False, default=0.0)
    BRST_BYTES_7 = Column(Float, nullable=False, default=0.0)

    BRST_PACKETS_0 = Column(Float, nullable=False, default=0.0)
    BRST_PACKETS_1 = Column(Float, nullable=False, default=0.0)

    flow_registry = relationship("FlowRegistry")