from concurrent.futures.thread import ThreadPoolExecutor

from app.pipeline.HTTPS.Initializer import HTTPSInference
from app.pipeline.ISCX_V2.Initializer import ISCXV2Inference
from app.pipeline.registry import get_pipeline_predict_fn, build_pipeline_inference
from app.settings import log


class PredictionQueue:
    def __init__(self, pipeline_name: str, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.pipeline_name = pipeline_name
        self.predict_fn = get_pipeline_predict_fn(pipeline_name)
        self.pipeline = build_pipeline_inference(pipeline_name)


    def enqueue(self, flow_id: str) -> None:
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

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False)