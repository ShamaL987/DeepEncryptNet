from pathlib import Path
import threading

from app.network_flow_tracker.flow_extractor import PacketStreamDivider
from app.pipeline.prediction_queue import PredictionQueue
from app.settings import log


def run_flow_daemon(cfg: dict, stop_event: threading.Event) -> None:
    try:
        divider = PacketStreamDivider(
            packet_csv=Path(cfg["csv_path"]),
            output_dir=Path(cfg["output_dir"]),
            offset_file=Path(cfg["offset_file"]),
            start_mode=cfg.get("mode", "live"),
            prediction_queue=PredictionQueue(),
            idle_timeout_sec=cfg.get("idle_timeout_sec", 30.0),
            poll_interval_sec=cfg.get("poll_interval_sec", 1.0),
            extract_features=cfg.get("enable_stats", True),
        )

        log.info("[FlowDaemon] Started")
        divider.run(stop_event)

    except Exception as exc:
        log.exception("[FlowDaemon] Fatal error", exc_info=exc)
