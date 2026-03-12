from concurrent.futures.thread import ThreadPoolExecutor
from app.settings import log


class PredictionQueue:
    def __init__(self, pipeline_name: str, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.pipeline_name = pipeline_name
        self.predict_fn = self._resolve_predict_fn()

    def _resolve_predict_fn(self):

        if self.pipeline_name == "ISCX_V1":
            from app.pipeline.ISCX_V1.caller import hybrid_pipeline
            return hybrid_pipeline

        # if self.pipeline_name == "ISCX_V2":
        #     from app.pipeline.ISCX_V2.caller import hybrid_pipeline
        #     return hybrid_pipeline
        #
        # if self.pipeline_name == "HTTPS":
        #     from app.pipeline.HTTPS.caller import hybrid_pipeline
        #     return hybrid_pipeline

        raise ValueError(f"Unsupported pipeline_name: {self.pipeline_name}")

    def enqueue(self, flow_id: str):
        self.executor.submit(self._predict, flow_id)

    def _predict(self, flow_id: str):
        try:
            result = self.predict_fn(flow_id)
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
