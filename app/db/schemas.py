from pydantic import BaseModel, Field

class FlowBase(BaseModel):
    flow_id: str
    protocol: str
    src_ip: str
    src_port: str
    dst_ip: str
    dst_port: str
    start_ts: float
    end_ts: float
    packet_count: int

class FlowRead(FlowBase):
    pass

class FlowPacketCreate(BaseModel):
    seq_no: int
    ts: float
    length: int | None = Field(default=None)
