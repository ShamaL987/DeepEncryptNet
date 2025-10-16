from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class Columns:
    timestamp: str = "timestamp"
    src_ip: str = "src_ip"
    src_port: str = "src_port"
    dst_ip: str = "dst_ip"
    dst_port: str = "dst_port"
    protocol: str = "protocol"
    length: str = "length"
    tcp_flags: str | None = "tcp_flags"   # optional; None if not present


@dataclass
class ReaderCfg:
    csv_path: str
    poll_interval_sec: float = 5.0
    max_concurrent_extractors: int = 5
    https_port: int = 443
    require_syn_for_start: bool = True
    columns: Columns = field(default_factory=Columns)   # ✅ correct way


@dataclass
class Settings:
    reader: ReaderCfg


def load_settings(path: str = None) -> Settings:
    """Load YAML configuration into dataclasses."""
    if path is None:
        path = Path(__file__).parent / "config.yaml"
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {cfg_path}")

    with open(cfg_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    reader_cfg = data.get("reader", {})
    columns_cfg = reader_cfg.get("columns", {})

    # Build dataclasses
    cols = Columns(**columns_cfg)
    reader = ReaderCfg(
        csv_path=reader_cfg.get("csv_path", "app/data/source.csv"),
        poll_interval_sec=reader_cfg.get("poll_interval_sec", 5),
        max_concurrent_extractors=reader_cfg.get("max_concurrent_extractors", 5),
        https_port=reader_cfg.get("https_port", 443),
        require_syn_for_start=reader_cfg.get("require_syn_for_start", True),
        columns=cols,
    )

    return Settings(reader=reader)
