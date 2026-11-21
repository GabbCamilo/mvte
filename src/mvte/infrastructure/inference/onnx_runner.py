"""Multi-backend ONNX Runtime execution wrapper (Windows DirectML / CUDA / ROCm / CPU)."""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Any

import numpy as np


def select_execution_providers(prefer_gpu: bool = True) -> list[str]:
    """Select available ONNX Runtime execution providers in priority order."""
    try:
        import onnxruntime as ort
    except ImportError:
        return ["CPUExecutionProvider"]

    available = set(ort.get_available_providers())
    if not prefer_gpu:
        return ["CPUExecutionProvider"]

    preferred_order = [
        "DmlExecutionProvider",
        "ROCMExecutionProvider",
        "CUDAExecutionProvider",
        "CPUExecutionProvider",
    ]
    selected = [p for p in preferred_order if p in available]
    return selected or ["CPUExecutionProvider"]


class OnnxSessionWrapper:
    """Lazy-loading ONNX Runtime session with explicit unload for VRAM budgeting."""

    def __init__(self, model_path: Path | str, prefer_gpu: bool = True) -> None:
        self.model_path = Path(model_path)
        self.prefer_gpu = prefer_gpu
        self._session: Any = None
        self.providers: list[str] = []

    def load(self) -> None:
        if self._session is not None:
            return
        if not self.model_path.exists():
            raise FileNotFoundError(f"ONNX model not found: {self.model_path}")
        import onnxruntime as ort

        self.providers = select_execution_providers(self.prefer_gpu)
        self._session = ort.InferenceSession(str(self.model_path), providers=self.providers)

    def run(self, inputs: dict[str, np.ndarray]) -> list[np.ndarray]:
        self.load()
        return self._session.run(None, inputs)

    def unload(self) -> None:
        if self._session is not None:
            del self._session
            self._session = None
            gc.collect()
