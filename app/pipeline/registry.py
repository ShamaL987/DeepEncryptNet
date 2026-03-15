from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class PipelineSpec:
    name: str
    caller_import: str
    caller_fn: str
    bundle_dir: Path
    initializer_import: str | None = None
    initializer_class: str | None = None


PIPELINE_SPECS: dict[str, PipelineSpec] = {
    "ISCX_V1": PipelineSpec(
        name="ISCX_V1",
        caller_import="app.pipeline.ISCX_V1.caller",
        caller_fn="hybrid_pipeline",
        bundle_dir=Path("app/pipeline/ISCX_V1/v8/bundle"),
        initializer_import=None,
        initializer_class=None,
    ),
    "ISCX_V2": PipelineSpec(
        name="ISCX_V2",
        caller_import="app.pipeline.ISCX_V2.caller",
        caller_fn="hybrid_pipeline",
        bundle_dir=Path("app/pipeline/ISCX_V2/v5/v1/bundle"),
        initializer_import="app.pipeline.ISCX_V2.Initializer",
        initializer_class="ISCXV2Inference",
    ),
    "HTTPS": PipelineSpec(
        name="HTTPS",
        caller_import="app.pipeline.HTTPS.caller",
        caller_fn="hybrid_pipeline",
        bundle_dir=Path("app/pipeline/HTTPS/v8/bundle"),
        initializer_import="app.pipeline.HTTPS.Initializer",
        initializer_class="HTTPSInference",
    ),
}


def get_pipeline_spec(pipeline_name: str) -> PipelineSpec:
    spec = PIPELINE_SPECS.get(pipeline_name)
    if spec is None:
        raise ValueError(f"Unsupported pipeline_name: {pipeline_name}")
    return spec


def get_pipeline_bundle_dir(pipeline_name: str) -> Path:
    return get_pipeline_spec(pipeline_name).bundle_dir


def get_inference_bundle_json_path(pipeline_name: str) -> Path:
    return get_pipeline_bundle_dir(pipeline_name) / "inference_bundle.json"


def get_pipeline_predict_fn(pipeline_name: str) -> Callable[..., Any]:
    spec = get_pipeline_spec(pipeline_name)
    module = importlib.import_module(spec.caller_import)
    return getattr(module, spec.caller_fn)


def build_pipeline_inference(pipeline_name: str):
    spec = get_pipeline_spec(pipeline_name)

    if spec.initializer_import is None or spec.initializer_class is None:
        return None

    module = importlib.import_module(spec.initializer_import)
    initializer_cls = getattr(module, spec.initializer_class)
    return initializer_cls(spec.bundle_dir)