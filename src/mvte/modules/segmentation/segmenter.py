"""Structural and character-level segmentation (separating container from text masks)."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Polygon

from mvte.domain.models.page import MaskKind, MaskLayer, VisualRegion
from mvte.domain.ports.vision import RawDetection
from mvte.infrastructure.inference.onnx_runner import OnnxSessionWrapper


class CtdOnnxMaskProvider:
    """Optional neural character-mask extractor using comictextdetector.pt.onnx (UNet+DBNet)."""

    def __init__(
        self,
        model_path: Path | str,
        input_size: int = 1024,
        mask_threshold: float = 0.30,
        prefer_gpu: bool = True,
    ) -> None:
        self.session = OnnxSessionWrapper(model_path, prefer_gpu=prefer_gpu)
        self.input_size = input_size
        self.mask_threshold = mask_threshold

    def predict_page_mask(self, image_bgr: np.ndarray) -> np.ndarray:
        orig_h, orig_w = image_bgr.shape[:2]
        resized = cv2.resize(image_bgr, (self.input_size, self.input_size), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        chw = np.transpose(rgb, (2, 0, 1))[None, ...]

        _, seg, _ = self.session.run({"images": chw})
        prob = np.squeeze(seg)
        binary = np.where(prob >= self.mask_threshold, 255, 0).astype(np.uint8)
        return cv2.resize(binary, (orig_w, orig_h), interpolation=cv2.INTER_NEAREST)

    def unload(self) -> None:
        self.session.unload()


class MaskSegmenter:
    """Produces polygon masks, structure masks, and character masks per detected region."""

    def __init__(self, ctd_mask_provider: CtdOnnxMaskProvider | None = None) -> None:
        self.ctd_mask_provider = ctd_mask_provider

    def segment(
        self, image_bgr: np.ndarray, detections: list[RawDetection]
    ) -> list[VisualRegion]:
        height, width = image_bgr.shape[:2]
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        neural_page_mask: np.ndarray | None = None
        if self.ctd_mask_provider is not None and detections:
            try:
                neural_page_mask = self.ctd_mask_provider.predict_page_mask(image_bgr)
            finally:
                self.ctd_mask_provider.unload()

        regions: list[VisualRegion] = []
        for det in detections:
            region_id = str(uuid.uuid4())
            polygon = self._normalize_polygon(det)

            structure_data = np.zeros((height, width), dtype=np.uint8)
            if det.mask is not None and det.mask.shape[:2] == (height, width):
                structure_data = np.where(det.mask > 0, 255, 0).astype(np.uint8)
            else:
                pts = np.array(polygon, dtype=np.int32)
                cv2.fillPoly(structure_data, [pts], 255)

            character_data = self._extract_character_mask(
                gray, structure_data, det, neural_page_mask=neural_page_mask
            )

            structure_layer = MaskLayer(
                id=str(uuid.uuid4()),
                kind=MaskKind.STRUCTURE,
                width=width,
                height=height,
                data=structure_data,
            )
            character_layer = MaskLayer(
                id=str(uuid.uuid4()),
                kind=MaskKind.CHARACTER,
                width=width,
                height=height,
                data=character_data,
            )

            regions.append(
                VisualRegion(
                    id=region_id,
                    kind=det.kind,
                    bbox=det.bbox,
                    confidence=det.confidence,
                    polygon=polygon,
                    structure_mask=structure_layer,
                    character_mask=character_layer,
                    source="auto",
                )
            )

        return regions

    @staticmethod
    def _normalize_polygon(det: RawDetection) -> list[tuple[int, int]]:
        if det.polygon and len(det.polygon) >= 3:
            poly = Polygon(det.polygon)
            if poly.is_valid and poly.area > 0:
                simplified = poly.simplify(1.5, preserve_topology=True)
                coords = list(simplified.exterior.coords)[:-1]
                if len(coords) >= 3:
                    return [(int(round(x)), int(round(y))) for x, y in coords]
        b = det.bbox
        return [(b.x1, b.y1), (b.x2, b.y1), (b.x2, b.y2), (b.x1, b.y2)]

    @staticmethod
    def _extract_character_mask(
        gray: np.ndarray,
        structure_mask: np.ndarray,
        det: RawDetection,
        *,
        neural_page_mask: np.ndarray | None = None,
    ) -> np.ndarray:
        """Separate character strokes inside the structural mask (neural CTD mask or Otsu fallback)."""
        char_mask = np.zeros_like(gray, dtype=np.uint8)
        b = det.bbox
        roi_struct = structure_mask[b.y1 : b.y2, b.x1 : b.x2]
        if roi_struct.size == 0:
            return char_mask

        if neural_page_mask is not None:
            roi_neural = neural_page_mask[b.y1 : b.y2, b.x1 : b.x2]
            intersected = cv2.bitwise_and(roi_neural, roi_struct)
            if np.any(intersected > 0):
                char_mask[b.y1 : b.y2, b.x1 : b.x2] = intersected
                return char_mask

        roi_gray = gray[b.y1 : b.y2, b.x1 : b.x2]
        inside_pixels = roi_gray[roi_struct > 0]
        if inside_pixels.size == 0:
            return char_mask

        median_bg = float(np.median(inside_pixels))
        if median_bg >= 128:
            _, binary = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        else:
            _, binary = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        interior_struct = cv2.erode(roi_struct, kernel, iterations=1)
        if np.any(interior_struct > 0):
            binary = cv2.bitwise_and(binary, interior_struct)
        else:
            binary = cv2.bitwise_and(binary, roi_struct)

        char_mask[b.y1 : b.y2, b.x1 : b.x2] = binary
        return char_mask


def resolve_default_segmenter(prefer_gpu: bool = True) -> MaskSegmenter:
    """Return MaskSegmenter with neural CTD mask refiner if comictextdetector.pt.onnx exists."""
    models_root = Path(os.environ.get("MVTE_MODELS_DIR") or Path(__file__).resolve().parents[4] / "models")
    ctd_path = models_root / "comictextdetector.pt.onnx"
    if ctd_path.exists():
        return MaskSegmenter(ctd_mask_provider=CtdOnnxMaskProvider(ctd_path, prefer_gpu=prefer_gpu))
    return MaskSegmenter()
