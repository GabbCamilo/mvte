"""Domain port contracts for Phase 2 OCR and linguistic reconstruction."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from mvte.domain.models.linguistic import TextBlock, TextOrientation
from mvte.domain.models.page import BoundingBox, ReadingDirection, VisualRegion


@dataclass
class OcrLine:
    """Single recognized line/fragment inside a cropped visual region."""

    text: str
    bbox: BoundingBox
    confidence: float
    orientation: TextOrientation = TextOrientation.HORIZONTAL
    language: str = "unknown"


class OcrBackendPort(Protocol):
    """Replaceable local OCR engine backend."""

    name: str

    def recognize(
        self, crop_bgr: np.ndarray, orientation: TextOrientation = TextOrientation.UNKNOWN
    ) -> list[OcrLine]:
        ...

    def unload(self) -> None:
        ...


class LinguisticReconstructorPort(Protocol):
    """Reconstructs coherent sentences and tokens from raw OCR lines."""

    def reconstruct(
        self,
        region: VisualRegion,
        ocr_lines: list[OcrLine],
        direction: ReadingDirection,
        reading_order: int = 0,
    ) -> TextBlock:
        ...
