from concurrent.futures.thread import ThreadPoolExecutor
import time

from app.pipeline.caller import hybrid_pipeline
from app.settings import log


class PredictionQueue:
    def __init__(self, max_workers: int = 2, result_callback=None, error_callback=None):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.result_callback = result_callback
        self.error_callback = error_callback

    def enqueue(self, flow_id: str):
        self.executor.submit(self._predict, flow_id)

    def _predict(self, flow_id: str):
        started = time.perf_counter()
        try:
            result = hybrid_pipeline(flow_id)
            decision = "Classify" if result["action"] == 0 else "Route"

            log.info(
                f"[PREDICT] {flow_id} -> {result['predicted_class']} "
                f"conf={result['confidence']:.3f} "
                f"decision={decision}"
            )

            if self.result_callback:
                latency_ms = (time.perf_counter() - started) * 1000.0
                self.result_callback(
                    latency_ms,
                    float(result.get("confidence", 0.0)),
                    int(result.get("action", 1)),
                )
        except Exception:
            log.exception(f"[PREDICT] failed for {flow_id}")
            if self.error_callback:
                self.error_callback()

    def shutdown(self):
        self.executor.shutdown(wait=False)
