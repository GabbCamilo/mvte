"""Layered page compositor preserving original image dimensions and lossless export."""

from __future__ import annotations

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from mvte.domain.models.rendering import TypographyPlan


class LayeredPageCompositor:
    """Renders translated text plans onto a copy of the cleaned page."""

    def compose(self, cleaned_bgr: np.ndarray, plans: list[TypographyPlan]) -> np.ndarray:
        rgb = cv2.cvtColor(cleaned_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        draw = ImageDraw.Draw(pil_img)

        for plan in plans:
            if not plan.wrapped_text.strip():
                continue
            font = self._load_font(plan.font_match.path, plan.font_size)
            left, top, right, bottom = draw.multiline_textbbox(
                (0, 0),
                plan.wrapped_text,
                font=font,
                spacing=plan.line_spacing,
                align=plan.align,
            )
            text_w = right - left
            text_h = bottom - top
            b = plan.usable_bbox
            cx = b.x1 + max(0, (b.width - text_w) // 2)
            cy = b.y1 + max(0, (b.height - text_h) // 2)

            if plan.outline_color is not None:
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx != 0 or dy != 0:
                            draw.multiline_text(
                                (cx + dx, cy + dy),
                                plan.wrapped_text,
                                font=font,
                                fill=plan.outline_color,
                                spacing=plan.line_spacing,
                                align=plan.align,
                            )

            draw.multiline_text(
                (cx, cy),
                plan.wrapped_text,
                font=font,
                fill=plan.text_color,
                spacing=plan.line_spacing,
                align=plan.align,
            )

        out_rgb = np.asarray(pil_img, dtype=np.uint8)
        return cv2.cvtColor(out_rgb, cv2.COLOR_RGB2BGR)

    @staticmethod
    def _load_font(font_path: str | None, size: int) -> ImageFont.ImageFont:
        if font_path:
            try:
                return ImageFont.truetype(font_path, size=size)
            except OSError:
                pass
        return ImageFont.load_default()
