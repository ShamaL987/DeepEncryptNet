from concurrent.futures.thread import ThreadPoolExecutor
from threading import Lock

from app.pipeline.registry import get_pipeline_predict_fn, build_pipeline_inference
from app.settings import log


class PredictionQueue:
    def __init__(self, pipeline_name: str, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.pipeline_name = pipeline_name
        self.predict_fn = get_pipeline_predict_fn(pipeline_name)
        self.pipeline = build_pipeline_inference(pipeline_name)

        self._pending_count = 0
        self._lock = Lock()

    def enqueue(self, flow_id: str) -> None:
        with self._lock:
            self._pending_count += 1

        self.executor.submit(self._predict, flow_id)

    def _predict(self, flow_id: str) -> None:
        try:
            result = self.predict_fn(flow_id, self.pipeline)
            decision = "Classify" if result["action"] == 0 else "Route"

            log.info(
                f"[PREDICT] {flow_id} -> {result['predicted_class']} "
                f"conf={result['confidence']:.3f} "
                f"decision={decision}"
            )
        except Exception:
            log.exception(f"[PREDICT] failed for {flow_id}")
        finally:
            with self._lock:
                self._pending_count = max(0, self._pending_count - 1)

    def get_pending_count(self) -> int:
        with self._lock:
            return self._pending_count

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False)