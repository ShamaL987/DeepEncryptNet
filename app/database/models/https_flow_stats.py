from sqlalchemy import Column, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from app.database.models.base import BaseModel


class HTTPSFlowStats(BaseModel):
    __tablename__ = "https_flow_stats"

    flow_id = Column(
        String,
        ForeignKey("flow_registry.flow_id", ondelete="CASCADE"),
        primary_key=True,
    )

    prefix_duration = Column(Float, nullable=False, default=0.0)
    prefix_bytes_per_second = Column(Float, nullable=False, default=0.0)
    prefix_pkts_per_second = Column(Float, nullable=False, default=0.0)
    prefix_fwd_pkt_share = Column(Float, nullable=False, default=0.0)
    prefix_fwd_byte_share = Column(Float, nullable=False, default=0.0)
    prefix_dir_switch_rate = Column(Float, nullable=False, default=0.0)
    prefix_mean_fwd_len = Column(Float, nullable=False, default=0.0)
    prefix_mean_rev_len = Column(Float, nullable=False, default=0.0)
    prefix_fwd_rev_mean_len_ratio = Column(Float, nullable=False, default=0.0)

    pkt_len_cv = Column(Float, nullable=False, default=0.0)
    pkt_len_iqr_ratio = Column(Float, nullable=False, default=0.0)
    iat_cv = Column(Float, nullable=False, default=0.0)
    iat_iqr_ratio = Column(Float, nullable=False, default=0.0)

    burst_count_per_second = Column(Float, nullable=False, default=0.0)
    burst_mean_bytes_per_packet = Column(Float, nullable=False, default=0.0)
    burst_std_bytes_per_packet = Column(Float, nullable=False, default=0.0)
    burst_top1_byte_share = Column(Float, nullable=False, default=0.0)
    burst_interval_cv = Column(Float, nullable=False, default=0.0)
    burst_interval_iqr_ratio = Column(Float, nullable=False, default=0.0)
    burst_duration_cv = Column(Float, nullable=False, default=0.0)
    burst_duration_iqr_ratio = Column(Float, nullable=False, default=0.0)

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

    BRST_INTERVALS_MEAN = Column(Float, nullable=False, default=0.0)
    BRST_INTERVALS_MAX = Column(Float, nullable=False, default=0.0)
    BRST_INTERVALS_STD = Column(Float, nullable=False, default=0.0)
    BRST_INTERVALS_25 = Column(Float, nullable=False, default=0.0)

    BRST_DURATION_MEAN = Column(Float, nullable=False, default=0.0)
    BRST_DURATION_MAX = Column(Float, nullable=False, default=0.0)
    BRST_DURATION_STD = Column(Float, nullable=False, default=0.0)

    flow_registry = relationship("FlowRegistry")