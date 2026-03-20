from __future__ import annotations

import copy
import threading
from typing import Any

from app.pipeline.prediction_queue import PredictionQueue
from app.services.flow_daemon import run_flow_daemon
from app.settings import log


class FlowDaemonController:
    def __init__(self, initial_config: dict[str, Any] | None = None) -> None:
        self._lock = threading.RLock()
        self._config: dict[str, Any] = copy.deepcopy(initial_config or {})
        self._thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None
        self._prediction_queue: PredictionQueue | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def get_config(self) -> dict[str, Any]:
        with self._lock:
            return copy.deepcopy(self._config)

    def get_prediction_queue_count(self) -> int:
        with self._lock:
            if self._prediction_queue is None:
                return 0
            return self._prediction_queue.get_pending_count()

    def update_config(self, new_config: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._config = copy.deepcopy(new_config)
            return {
                "updated": True,
                "restart_required": self.is_running,
                "config": copy.deepcopy(self._config),
            }

    def start(self) -> dict[str, Any]:
        with self._lock:
            if self.is_running:
                return {
                    "started": False,
                    "status": "already_running",
                }

            self._stop_event = threading.Event()
            self._prediction_queue = PredictionQueue(self._config["feature_pipeline"])
            self._thread = threading.Thread(
                target=run_flow_daemon,
                args=(
                    copy.deepcopy(self._config),
                    self._stop_event,
                    self._prediction_queue,
                ),
                daemon=True,
                name="flow-daemon",
            )
            self._thread.start()

        log.info("[FlowDaemonController] Flow daemon started")

        return {
            "started": True,
            "status": "running",
        }

    def stop(self, timeout: int = 10) -> dict[str, Any]:
        with self._lock:
            if not self.is_running:
                return {
                    "stopped": False,
                    "status": "already_stopped",
                }

            stop_event = self._stop_event
            thread = self._thread
            prediction_queue = self._prediction_queue

            if stop_event is not None:
                stop_event.set()

        if thread is not None:
            thread.join(timeout=timeout)

        clean_shutdown = thread is not None and not thread.is_alive()

        if prediction_queue is not None:
            prediction_queue.shutdown()

        with self._lock:
            if clean_shutdown:
                self._thread = None
                self._stop_event = None
                self._prediction_queue = None
                log.info("[FlowDaemonController] Flow daemon stopped")
            else:
                log.warning("[FlowDaemonController] Flow daemon did not shut down cleanly")

            return {
                "stopped": clean_shutdown,
                "status": "stopped" if clean_shutdown else "shutdown_timeout",
            }

    def restart(self, timeout: int = 10) -> dict[str, Any]:
        stop_result = self.stop(timeout=timeout)
        start_result = self.start()
        return {
            "stop": stop_result,
            "start": start_result,
            "status": self.get_status(),
        }

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "is_running": self.is_running,
                "thread_name": self._thread.name if self._thread else None,
                "config": copy.deepcopy(self._config),
                "prediction_queue_count": (
                    self._prediction_queue.get_pending_count()
                    if self._prediction_queue is not None
                    else 0
                ),
            }