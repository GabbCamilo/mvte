"""Domain port contracts for Phase 4 text cleaning, typography, and rendering."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from mvte.domain.models.page import PageDocument, VisualRegion
from mvte.domain.models.rendering import CleanedPageResult, TypographyPlan


class InpainterPort(Protocol):
    """Replaceable background reconstruction backend for non-uniform regions."""

    name: str

    def inpaint(self, image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        ...

    def unload(self) -> None:
        ...


class TextCleanerPort(Protocol):
    """Removes original text non-destructively using character masks."""

    def clean(self, image_bgr: np.ndarray, document: PageDocument) -> CleanedPageResult:
        ...


class TypographyEnginePort(Protocol):
    """Matches local fonts and fits translated text without truncation."""

    def plan_region(
        self, image_bgr: np.ndarray, region: VisualRegion, translated_text: str
    ) -> TypographyPlan:
        ...


class PageCompositorPort(Protocol):
    """Composes cleaned image and typography plans into a lossless output."""

    def compose(
        self, cleaned_bgr: np.ndarray, plans: list[TypographyPlan]
    ) -> np.ndarray:
        ...
