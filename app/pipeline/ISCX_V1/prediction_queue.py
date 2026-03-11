from concurrent.futures.thread import ThreadPoolExecutor

from app.pipeline.ISCX_V1.caller import hybrid_pipeline
from app.settings import log


class PredictionQueue:
    def __init__(self, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def enqueue(self, flow_id: str):
        self.executor.submit(self._predict, flow_id)

    def _predict(self, flow_id: str):
        try:
            result = hybrid_pipeline(flow_id)
            decision = "Classify" if result["action"] == 0 else "Route"

            log.info(
                f"[PREDICT] {flow_id} -> {result['predicted_class']} "
                f"conf={result['confidence']:.3f} "
                f"decision={decision}"
            )
        except Exception:
            log.exception(f"[PREDICT] failed for {flow_id}")

    def shutdown(self):
        self.executor.shutdown(wait=False)
