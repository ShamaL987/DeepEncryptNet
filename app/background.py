from __future__ import annotations
import threading
import time
from pathlib import Path
from typing import Optional

from app.flow_daemon import tail_loop  # reuse your tail_loop(cfg)
from app.settings import load_settings # your yaml/pyproject loader returning a dict

class FlowDaemonRunner:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="flow-daemon", daemon=True)
        self._thread.start()

    def _run(self):
        # Small wrapper: forward stop flag into tail_loop via cfg or a global
        # Easiest: patch tail_loop to accept stop_event and check it in the while True loop.
        tail_loop(self.cfg, stop_event=self._stop)

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=10)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())
