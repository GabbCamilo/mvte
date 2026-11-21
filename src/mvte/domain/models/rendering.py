"""Domain models for Phase 4 text cleaning, typography, and layered rendering."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from mvte.domain.models.page import BoundingBox


@dataclass
class FontMatch:
    """Result of local font matching (explicitly tracks non-exactness)."""

    family: str
    path: str | None
    weight: str = "regular"
    italic: bool = False
    is_exact_match: bool = False
    alternatives: list[str] = field(default_factory=list)


@dataclass
class TypographyPlan:
    """Layout and styling plan to render translated text inside a target region."""

    region_id: str
    text: str
    wrapped_text: str
    usable_bbox: BoundingBox
    font_match: FontMatch
    font_size: int
    line_spacing: int
    align: str = "center"
    text_color: tuple[int, int, int] = (0, 0, 0)
    outline_color: tuple[int, int, int] | None = None
    needs_manual_review: bool = False
    overflow_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "region_id": self.region_id,
            "text": self.text,
            "wrapped_text": self.wrapped_text,
            "usable_bbox": self.usable_bbox.to_dict(),
            "font_family": self.font_match.family,
            "font_path": self.font_match.path,
            "is_exact_font_match": self.font_match.is_exact_match,
            "font_size": self.font_size,
            "line_spacing": self.line_spacing,
            "align": self.align,
            "needs_manual_review": self.needs_manual_review,
            "overflow_reason": self.overflow_reason,
        }


@dataclass
class CleaningReportEntry:
    """Per-region cleaning decision for auditability."""

    region_id: str
    strategy: str  # "uniform_fill" | "inpaint" | "skipped"
    border_std_dev: float


@dataclass
class CleanedPageResult:
    """Cleaned image (separate from original) and per-region cleaning diagnostics."""

    cleaned_bgr: np.ndarray
    combined_mask: np.ndarray
    reports: list[CleaningReportEntry] = field(default_factory=list)


@dataclass
class ReconstructionResult:
    """Final Phase 4 outputs preserving original dimensions."""

    cleaned_path: str | None
    translated_path: str | None
    plans: list[TypographyPlan] = field(default_factory=list)
    cleaning_reports: list[CleaningReportEntry] = field(default_factory=list)
