"""Local multilingual OCR backends and orientation estimation (Phase 2)."""

from __future__ import annotations

import gc
from typing import Callable

import cv2
import numpy as np

from mvte.domain.models.linguistic import TextOrientation
from mvte.domain.models.page import BoundingBox
from mvte.domain.ports.ocr import OcrBackendPort, OcrLine


def estimate_text_orientation(crop_bgr: np.ndarray) -> TextOrientation:
    """Estimate whether a text crop is predominantly vertical or horizontal."""
    if crop_bgr.size == 0:
        return TextOrientation.UNKNOWN
    h, w = crop_bgr.shape[:2]
    if h > w * 1.35:
        return TextOrientation.VERTICAL
    if w > h * 1.15:
        return TextOrientation.HORIZONTAL

    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
    grad_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    energy_x = float(np.mean(np.abs(grad_x)))
    energy_y = float(np.mean(np.abs(grad_y)))
    if energy_y > energy_x * 1.25:
        return TextOrientation.HORIZONTAL
    if energy_x > energy_y * 1.25:
        return TextOrientation.VERTICAL
    return TextOrientation.HORIZONTAL


class RapidOcrAdapter:
    """ONNX-based multilingual OCR adapter using rapidocr-onnxruntime (no PaddlePaddle)."""

    name = "rapidocr_onnx"

    def __init__(self) -> None:
        self._engine = None

    def _load(self) -> None:
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR

            self._engine = RapidOCR()

    def recognize(
        self, crop_bgr: np.ndarray, orientation: TextOrientation = TextOrientation.UNKNOWN
    ) -> list[OcrLine]:
        self._load()
        resolved_orientation = (
            estimate_text_orientation(crop_bgr)
            if orientation == TextOrientation.UNKNOWN
            else orientation
        )
        result, _ = self._engine(crop_bgr)
        if not result:
            return []

        lines: list[OcrLine] = []
        for item in result:
            poly, text, conf = item[0], str(item[1]), float(item[2])
            xs = [int(round(pt[0])) for pt in poly]
            ys = [int(round(pt[1])) for pt in poly]
            bbox = BoundingBox(min(xs), min(ys), max(max(xs), min(xs) + 1), max(max(ys), min(ys) + 1))
            lines.append(
                OcrLine(
                    text=text,
                    bbox=bbox,
                    confidence=conf,
                    orientation=resolved_orientation,
                )
            )
        return lines

    def unload(self) -> None:
        if self._engine is not None:
            del self._engine
            self._engine = None
            gc.collect()


class MangaOcrAdapter:
    """Optional Japanese-specialized local OCR adapter using manga-ocr."""

    name = "manga_ocr"

    def __init__(self) -> None:
        self._engine = None

    def _load(self) -> None:
        if self._engine is None:
            from manga_ocr import MangaOcr

            self._engine = MangaOcr()

    def recognize(
        self, crop_bgr: np.ndarray, orientation: TextOrientation = TextOrientation.UNKNOWN
    ) -> list[OcrLine]:
        from PIL import Image

        self._load()
        h, w = crop_bgr.shape[:2]
        rgb = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2RGB)
        text = str(self._engine(Image.fromarray(rgb))).strip()
        if not text:
            return []
        resolved = (
            estimate_text_orientation(crop_bgr)
            if orientation == TextOrientation.UNKNOWN
            else orientation
        )
        return [
            OcrLine(
                text=text,
                bbox=BoundingBox(0, 0, max(1, w), max(1, h)),
                confidence=0.9,
                orientation=resolved,
                language="ja",
            )
        ]

    def unload(self) -> None:
        if self._engine is not None:
            del self._engine
            self._engine = None
            gc.collect()


class OcrRegistry:
    """Registry allowing runtime selection/replacement of OCR backends."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], OcrBackendPort]] = {}

    def register(self, name: str, factory: Callable[[], OcrBackendPort]) -> None:
        self._factories[name] = factory

    def create(self, name: str) -> OcrBackendPort:
        if name not in self._factories:
            available = ", ".join(sorted(self._factories))
            raise KeyError(f"Unknown OCR backend '{name}'. Available: {available}")
        return self._factories[name]()

    def list_backends(self) -> list[str]:
        return sorted(self._factories)
