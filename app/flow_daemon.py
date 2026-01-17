import time
from pathlib import Path
import threading

from app.network_flow_tracker.flow_extractor import PacketStreamDivider
from app.pipeline.prediction_queue import PredictionQueue
from app.settings import log


def run_flow_daemon(cfg: dict, stop_event: threading.Event) -> None:
    ready_dir = Path(cfg["ready_dir"])
    processing_dir = Path(cfg["processing_dir"])
    processed_dir = Path(cfg["processed_dir"])

    processing_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    prediction_queue = PredictionQueue()

    log.info("[FlowDaemon] Watching batch directory")

    try:
        while not stop_event.is_set():
            batches = sorted(ready_dir.glob("*.csv"))

            if not batches:
                time.sleep(cfg.get("poll_interval_sec", 1.0))
                continue

            batch = batches[0]
            processing_path = processing_dir / batch.name

            # atomic move
            batch.replace(processing_path)
            log.info(f"[FlowDaemon] Processing {processing_path.name}")

            divider = PacketStreamDivider(
                packet_csv=processing_path,
                output_dir=Path(cfg["streams_dir"]),
                extract_features=cfg.get("enable_stats", True),
                prediction_queue=prediction_queue,
                idle_timeout_sec=cfg.get("idle_timeout_sec", 30.0),
                max_packets=cfg.get("max_packets", 100),
                max_duration_sec=cfg.get("max_duration_sec", 20.0),
            )

            divider.run(stop_event=stop_event, batch_id=batch.name)

            processed_path = processed_dir / processing_path.name
            processing_path.replace(processed_path)

            log.info(f"[FlowDaemon] Finished {processed_path.name}")

    except Exception as exc:
        log.exception("[FlowDaemon] Fatal error", exc_info=exc)
