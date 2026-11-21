"""Domain port contracts (Protocols) for Phase 1 vision subsystems."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from mvte.domain.models.page import (
    BoundingBox,
    Panel,
    ReadingDirection,
    RegionKind,
    TextRegionAssociation,
    VisualRegion,
)


@dataclass
class RawDetection:
    """Backend-agnostic detection output before segmentation refinement."""

    kind: RegionKind
    bbox: BoundingBox
    confidence: float
    polygon: list[tuple[int, int]] | None = None
    mask: np.ndarray | None = None


class PageAnalyzerPort(Protocol):
    """Detects page panels and computes reading order."""

    def analyze(self, image_bgr: np.ndarray, direction: ReadingDirection) -> list[Panel]:
        ...


class VisualDetectorPort(Protocol):
    """Replaceable visual structure detector."""

    name: str

    def detect(self, image_bgr: np.ndarray) -> list[RawDetection]:
        ...

    def unload(self) -> None:
        ...


class SegmenterPort(Protocol):
    """Produces polygon and pixel masks (structural vs character) for detections."""

    def segment(
        self, image_bgr: np.ndarray, detections: list[RawDetection]
    ) -> list[VisualRegion]:
        ...


class RegionAssociatorPort(Protocol):
    """Associates text regions with enclosing visual containers and panels."""

    def associate(
        self, panels: list[Panel], regions: list[VisualRegion]
    ) -> list[TextRegionAssociation]:
        ...
