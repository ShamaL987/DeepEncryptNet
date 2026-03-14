from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from statistics import median
from typing import Any

from app.flow_daemon import run_flow_daemon
from app.settings import log


@dataclass
class DaemonStatsSnapshot:
    packets_per_sec: float
    flows_per_sec: float
    feature_latency_ms_avg: float | None
    inference_latency_ms_avg: float | None
    confidence_median: float | None
    route_rate: float
    error_count: int


class DaemonController:
    def __init__(self, initial_config: dict[str, Any]):
        self._config_lock = threading.Lock()
        self._runner_lock = threading.Lock()

        self._config = dict(initial_config)
        self._thread: threading.Thread | None = None
        self._stop_event: threading.Event | None = None

        self._events_lock = threading.Lock()
        self._packet_events = deque(maxlen=5000)
        self._flow_events = deque(maxlen=5000)
        self._feature_latencies_ms = deque(maxlen=5000)
        self._inference_latencies_ms = deque(maxlen=5000)
        self._confidence_values = deque(maxlen=5000)
        self._route_decisions = deque(maxlen=5000)
        self._errors = 0

    def start(self) -> bool:
        with self._runner_lock:
            if self.is_running:
                return False

            self._stop_event = threading.Event()
            self._thread = threading.Thread(
                target=run_flow_daemon,
                args=(self.get_config(), self._stop_event),
                kwargs={
                    "stats_callback": self.record_flow_batch_stats,
                    "feature_latency_callback": self.record_feature_latency,
                    "result_callback": self.record_inference_result,
                    "error_callback": self.record_error,
                },
                daemon=True,
                name="flow-daemon",
            )
            log.info("[DaemonController] Starting flow daemon")
            self._thread.start()
            return True

    def stop(self) -> bool:
        with self._runner_lock:
            if not self.is_running:
                return False

            log.info("[DaemonController] Stopping flow daemon")
            if self._stop_event:
                self._stop_event.set()
            if self._thread:
                self._thread.join(timeout=10)
            return True

    def restart(self) -> None:
        self.stop()
        self.start()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def get_config(self) -> dict[str, Any]:
        with self._config_lock:
            return dict(self._config)

    def update_config(self, updates: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "poll_interval_sec",
            "idle_timeout_sec",
            "max_packets",
            "max_duration_sec",
            "enable_stats",
        }
        cleaned = {k: v for k, v in updates.items() if k in allowed}
        with self._config_lock:
            self._config.update(cleaned)
            return dict(self._config)

    def record_flow_batch_stats(self, packet_count: int, flow_count: int) -> None:
        now = time.time()
        with self._events_lock:
            if packet_count > 0:
                self._packet_events.append((now, packet_count))
            if flow_count > 0:
                self._flow_events.append((now, flow_count))

    def record_feature_latency(self, latency_ms: float) -> None:
        with self._events_lock:
            self._feature_latencies_ms.append((time.time(), latency_ms))

    def record_inference_result(self, latency_ms: float, confidence: float, action: int) -> None:
        now = time.time()
        with self._events_lock:
            self._inference_latencies_ms.append((now, latency_ms))
            self._confidence_values.append((now, confidence))
            self._route_decisions.append((now, action))

    def record_error(self) -> None:
        with self._events_lock:
            self._errors += 1

    def _windowed_values(self, entries: deque[tuple[float, float]], window_sec: int) -> list[float]:
        cutoff = time.time() - window_sec
        return [value for ts, value in entries if ts >= cutoff]

    def _windowed_sum_per_second(self, entries: deque[tuple[float, float]], window_sec: int) -> float:
        values = self._windowed_values(entries, window_sec)
        return (sum(values) / window_sec) if values else 0.0

    def stats_snapshot(self, window_sec: int = 60) -> DaemonStatsSnapshot:
        with self._events_lock:
            feature_vals = self._windowed_values(self._feature_latencies_ms, window_sec)
            inference_vals = self._windowed_values(self._inference_latencies_ms, window_sec)
            confidence_vals = self._windowed_values(self._confidence_values, window_sec)
            actions = self._windowed_values(self._route_decisions, window_sec)

            routed = sum(1 for a in actions if int(a) == 1)
            total = len(actions)

            return DaemonStatsSnapshot(
                packets_per_sec=self._windowed_sum_per_second(self._packet_events, window_sec),
                flows_per_sec=self._windowed_sum_per_second(self._flow_events, window_sec),
                feature_latency_ms_avg=(sum(feature_vals) / len(feature_vals)) if feature_vals else None,
                inference_latency_ms_avg=(sum(inference_vals) / len(inference_vals)) if inference_vals else None,
                confidence_median=median(confidence_vals) if confidence_vals else None,
                route_rate=(routed / total) if total else 0.0,
                error_count=self._errors,
            )
