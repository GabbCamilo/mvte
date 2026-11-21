"""Local typography analysis, font matching, and non-truncating text fitting (Phase 4)."""

from __future__ import annotations

import os
from pathlib import Path
from textwrap import wrap

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from mvte.domain.models.page import BoundingBox, RegionKind, VisualRegion
from mvte.domain.models.rendering import FontMatch, TypographyPlan


class LocalFontCatalog:
    """Discovers locally installed TrueType/OpenType fonts on Windows and Linux."""

    DEFAULT_DIRS = (
        Path("C:/Windows/Fonts"),
        Path("/usr/share/fonts"),
        Path.home() / ".local/share/fonts",
    )

    def __init__(self, extra_dirs: list[Path | str] | None = None) -> None:
        self._fonts: dict[str, Path] = {}
        dirs = [Path(d) for d in (extra_dirs or [])] + list(self.DEFAULT_DIRS)
        self._scan(dirs)

    def _scan(self, dirs: list[Path]) -> None:
        for base in dirs:
            if not base.exists() or not base.is_dir():
                continue
            for root, _, files in os.walk(base):
                for fname in files:
                    if fname.lower().endswith((".ttf", ".otf")):
                        stem = Path(fname).stem
                        self._fonts.setdefault(stem, Path(root) / fname)

    def match(self, prefer_bold: bool = False, prefer_italic: bool = False) -> FontMatch:
        if not self._fonts:
            return FontMatch(family="PIL_Default", path=None, is_exact_match=False, alternatives=[])

        ranked: list[tuple[int, str, Path]] = []
        preferred_names = ("arial", "noto", "liberation", "dejavu", "segoe", "roboto", "anime")
        for name, path in self._fonts.items():
            lower = name.lower()
            score = 0
            if any(p in lower for p in preferred_names):
                score += 10
            if prefer_bold and ("bold" in lower or "bd" in lower):
                score += 5
            if prefer_italic and ("italic" in lower or "oblique" in lower):
                score += 5
            if not prefer_bold and "bold" not in lower:
                score += 2
            ranked.append((score, name, path))

        ranked.sort(key=lambda item: (-item[0], item[1]))
        best_score, best_name, best_path = ranked[0]
        alternatives = [item[1] for item in ranked[1:5]]
        return FontMatch(
            family=best_name,
            path=str(best_path),
            weight="bold" if prefer_bold else "regular",
            italic=prefer_italic,
            is_exact_match=False,  # Never claim exact recovery of proprietary comic fonts
            alternatives=alternatives,
        )


class TypographyEngine:
    """Computes usable interior area and fits translated text without truncating words."""

    def __init__(
        self,
        catalog: LocalFontCatalog | None = None,
        init_font_size: int = 24,
        min_font_size: int = 10,
    ) -> None:
        self.catalog = catalog or LocalFontCatalog()
        self.init_font_size = init_font_size
        self.min_font_size = min_font_size

    def plan_region(
        self, image_bgr: np.ndarray, region: VisualRegion, translated_text: str
    ) -> TypographyPlan:
        usable_bbox = self._compute_usable_bbox(region)
        prefer_bold = region.kind in (RegionKind.SFX, RegionKind.NARRATION_BOX)
        font_match = self.catalog.match(prefer_bold=prefer_bold, prefer_italic=False)
        text_color, outline_color = self._pick_contrast_colors(image_bgr, usable_bbox)

        roi_w = max(16, usable_bbox.width)
        roi_h = max(16, usable_bbox.height)
        wrapped, chosen_size, spacing, needs_review, reason = self._fit_text(
            translated_text.strip(), font_match.path, roi_w, roi_h
        )

        return TypographyPlan(
            region_id=region.id,
            text=translated_text,
            wrapped_text=wrapped,
            usable_bbox=usable_bbox,
            font_match=font_match,
            font_size=chosen_size,
            line_spacing=spacing,
            align="center",
            text_color=text_color,
            outline_color=outline_color,
            needs_manual_review=needs_review,
            overflow_reason=reason,
        )

    @staticmethod
    def _compute_usable_bbox(region: VisualRegion) -> BoundingBox:
        b = region.bbox
        if region.structure_mask is None or region.structure_mask.data is None:
            pad_x = max(4, int(b.width * 0.12))
            pad_y = max(4, int(b.height * 0.12))
            return BoundingBox(
                min(b.x2 - 1, b.x1 + pad_x),
                min(b.y2 - 1, b.y1 + pad_y),
                max(b.x1 + pad_x + 1, b.x2 - pad_x),
                max(b.y1 + pad_y + 1, b.y2 - pad_y),
            )

        mask_roi = region.structure_mask.data[b.y1 : b.y2, b.x1 : b.x2]
        if not np.any(mask_roi):
            return b
        dist = cv2.distanceTransform(np.where(mask_roi > 0, 1, 0).astype(np.uint8), cv2.DIST_L2, 5)
        max_dist = float(np.max(dist))
        interior = mask_roi > 0 if max_dist < 4 else dist >= (max_dist * 0.35)
        ys, xs = np.where(interior)
        if xs.size == 0 or ys.size == 0:
            return b
        return BoundingBox(
            b.x1 + int(xs.min()),
            b.y1 + int(ys.min()),
            b.x1 + int(xs.max()) + 1,
            b.y1 + int(ys.max()) + 1,
        )

    @staticmethod
    def _pick_contrast_colors(
        image_bgr: np.ndarray, bbox: BoundingBox
    ) -> tuple[tuple[int, int, int], tuple[int, int, int] | None]:
        roi = image_bgr[bbox.y1 : bbox.y2, bbox.x1 : bbox.x2]
        if roi.size == 0:
            return (0, 0, 0), None
        luminance = float(np.mean(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)))
        if luminance >= 128:
            return (10, 10, 10), (255, 255, 255)
        return (245, 245, 245), (0, 0, 0)

    def _fit_text(
        self, text: str, font_path: str | None, roi_w: int, roi_h: int
    ) -> tuple[str, int, int, bool, str]:
        if not text:
            return "", self.init_font_size, 4, False, ""

        dummy = Image.new("RGB", (max(64, roi_w + 20), max(64, roi_h + 20)))
        draw = ImageDraw.Draw(dummy)

        for size in range(self.init_font_size, self.min_font_size - 1, -1):
            font = self._load_font(font_path, size)
            for spacing in (4, 2, 1):
                for cols in range(max(4, len(text)), 3, -2):
                    candidate = "\n".join(
                        wrap(text, width=cols, break_long_words=False, break_on_hyphens=False)
                    )
                    if not candidate:
                        continue
                    left, top, right, bottom = draw.multiline_textbbox(
                        (0, 0), candidate, font=font, spacing=spacing, align="center"
                    )
                    if (right - left) <= roi_w and (bottom - top) <= roi_h:
                        return candidate, size, spacing, False, ""

        # Fallback at min_font_size without truncating any words
        fallback_cols = max(6, roi_w // max(5, self.min_font_size // 2))
        wrapped = "\n".join(
            wrap(text, width=fallback_cols, break_long_words=False, break_on_hyphens=False)
        )
        return wrapped or text, self.min_font_size, 1, True, "text_exceeds_min_legible_box"

    @staticmethod
    def _load_font(font_path: str | None, size: int) -> ImageFont.ImageFont:
        if font_path and Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size=size)
            except OSError:
                pass
        return ImageFont.load_default()
