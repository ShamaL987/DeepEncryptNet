import yaml
from pathlib import Path

def load_settings():
    # Load YAML or return a dict; adapt to your current config structure
    p = Path("app/config.yaml")
    data = {}
    if p.exists():
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    # Ensure defaults
    data.setdefault("flow_daemon", {
        "csv_path": "../AIMchat2.csv",
        "poll_interval_sec": 2.0,
        "idle_timeout_sec": 15.0,
        "active_timeout_sec": 1800.0,
        "https_only": True,
        "protocol_filter": ["TCP"],
        "output_dir": "app/data/extracted",
        "db_path": "app/data/flow_state.db",
        "columns": {
            "timestamp": "timestamp",
            "src_ip": "src_ip",
            "src_port": "src_port",
            "dst_ip": "dst_ip",
            "dst_port": "dst_port",
            "protocol": "protocol",
        }
    })
    return data
