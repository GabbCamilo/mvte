"""Selective text cleaning and inpainting (inspired by PanelCleaner's border uniformity)."""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from mvte.domain.models.page import PageDocument
from mvte.domain.models.rendering import CleanedPageResult, CleaningReportEntry
from mvte.domain.ports.rendering import InpainterPort
from mvte.infrastructure.inference.onnx_runner import OnnxSessionWrapper


class OpenCvTeleaInpainter:
    """Fast local CPU inpainter using OpenCV Telea algorithm."""

    name = "opencv_telea"

    def __init__(self, radius: int = 3) -> None:
        self.radius = radius

    def inpaint(self, image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        mask_u8 = np.where(mask > 0, 255, 0).astype(np.uint8)
        return cv2.inpaint(image_bgr, mask_u8, self.radius, cv2.INPAINT_TELEA)

    def unload(self) -> None:
        return None


class LamaOnnxInpainter:
    """Replaceable ONNX-based LaMa inpainter for complex/textured backgrounds."""

    name = "lama_onnx"

    def __init__(self, model_path: Path | str, prefer_gpu: bool = True) -> None:
        self.session = OnnxSessionWrapper(model_path, prefer_gpu=prefer_gpu)

    def inpaint(self, image_bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        self.session.load()
        h, w = image_bgr.shape[:2]
        pad_h = (8 - h % 8) % 8
        pad_w = (8 - w % 8) % 8
        img_pad = cv2.copyMakeBorder(image_bgr, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT)
        mask_pad = cv2.copyMakeBorder(
            np.where(mask > 0, 255, 0).astype(np.uint8), 0, pad_h, 0, pad_w, cv2.BORDER_CONSTANT, value=0
        )

        rgb = cv2.cvtColor(img_pad, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        img_tensor = np.transpose(rgb, (2, 0, 1))[None, ...]
        mask_tensor = (mask_pad.astype(np.float32) / 255.0)[None, None, ...]

        inputs = self.session._session.get_inputs()
        outputs = self.session.run({inputs[0].name: img_tensor, inputs[1].name: mask_tensor})
        out = np.clip(np.transpose(outputs[0][0], (1, 2, 0)) * 255.0, 0, 255).astype(np.uint8)
        out_bgr = cv2.cvtColor(out, cv2.COLOR_RGB2BGR)
        return out_bgr[:h, :w]

    def unload(self) -> None:
        self.session.unload()


class InpainterRegistry:
    """Registry for replaceable inpainting backends."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], InpainterPort]] = {}

    def register(self, name: str, factory: Callable[[], InpainterPort]) -> None:
        self._factories[name] = factory

    def create(self, name: str) -> InpainterPort:
        if name not in self._factories:
            available = ", ".join(sorted(self._factories))
            raise KeyError(f"Unknown inpainter '{name}'. Available: {available}")
        return self._factories[name]()


class SelectiveTextCleaner:
    """Removes text using character masks and border-uniformity-driven inpainting."""

    def __init__(
        self,
        inpainter: InpainterPort | None = None,
        uniform_std_threshold: float = 14.0,
        mask_dilation_px: int = 3,
    ) -> None:
        self.inpainter = inpainter or OpenCvTeleaInpainter()
        self.uniform_std_threshold = uniform_std_threshold
        self.mask_dilation_px = mask_dilation_px

    def clean(self, image_bgr: np.ndarray, document: PageDocument) -> CleanedPageResult:
        cleaned = image_bgr.copy()
        h, w = cleaned.shape[:2]
        combined_mask = np.zeros((h, w), dtype=np.uint8)
        inpaint_mask = np.zeros((h, w), dtype=np.uint8)
        reports: list[CleaningReportEntry] = []

        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (self.mask_dilation_px * 2 + 1, self.mask_dilation_px * 2 + 1)
        )
        border_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

        for region in document.regions:
            if region.character_mask is None or region.character_mask.data is None:
                reports.append(CleaningReportEntry(region.id, "skipped", 0.0))
                continue

            char_mask = np.where(region.character_mask.data > 0, 255, 0).astype(np.uint8)
            if not np.any(char_mask):
                reports.append(CleaningReportEntry(region.id, "skipped", 0.0))
                continue

            dilated = cv2.dilate(char_mask, kernel, iterations=1)
            # Keep cleaning strictly inside structural mask if available
            if region.structure_mask is not None and region.structure_mask.data is not None:
                struct_u8 = np.where(region.structure_mask.data > 0, 255, 0).astype(np.uint8)
                dilated = cv2.bitwise_and(dilated, struct_u8)

            ring = cv2.subtract(cv2.dilate(dilated, border_kernel, iterations=1), dilated)
            ring_pixels = cleaned[ring > 0]
            if ring_pixels.size == 0:
                reports.append(CleaningReportEntry(region.id, "skipped", 0.0))
                continue

            border_std = float(np.mean(np.std(ring_pixels.astype(np.float32), axis=0)))
            combined_mask = cv2.bitwise_or(combined_mask, dilated)

            if border_std <= self.uniform_std_threshold:
                fill_color = np.median(ring_pixels, axis=0).astype(np.uint8)
                cleaned[dilated > 0] = fill_color
                reports.append(CleaningReportEntry(region.id, "uniform_fill", round(border_std, 3)))
            else:
                inpaint_mask = cv2.bitwise_or(inpaint_mask, dilated)
                reports.append(CleaningReportEntry(region.id, "inpaint", round(border_std, 3)))

        if np.any(inpaint_mask):
            try:
                cleaned = self.inpainter.inpaint(cleaned, inpaint_mask)
            finally:
                self.inpainter.unload()
                gc.collect()

        return CleanedPageResult(cleaned_bgr=cleaned, combined_mask=combined_mask, reports=reports)
