"""Structural and character-level segmentation (separating container from text masks)."""

from __future__ import annotations

import uuid

import cv2
import numpy as np
from shapely.geometry import Polygon

from mvte.domain.models.page import MaskKind, MaskLayer, VisualRegion
from mvte.domain.ports.vision import RawDetection


class MaskSegmenter:
    """Produces polygon masks, structure masks, and character masks per detected region."""

    def segment(
        self, image_bgr: np.ndarray, detections: list[RawDetection]
    ) -> list[VisualRegion]:
        height, width = image_bgr.shape[:2]
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
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

            character_data = self._extract_character_mask(gray, structure_data, det)

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
        gray: np.ndarray, structure_mask: np.ndarray, det: RawDetection
    ) -> np.ndarray:
        """Separate character strokes inside the structural mask from the background."""
        char_mask = np.zeros_like(gray, dtype=np.uint8)
        b = det.bbox
        roi_gray = gray[b.y1 : b.y2, b.x1 : b.x2]
        roi_struct = structure_mask[b.y1 : b.y2, b.x1 : b.x2]
        if roi_gray.size == 0:
            return char_mask

        inside_pixels = roi_gray[roi_struct > 0]
        if inside_pixels.size == 0:
            return char_mask

        # Determine polarity: dark text on light background vs light text on dark background
        median_bg = float(np.median(inside_pixels))
        if median_bg >= 128:
            _, binary = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        else:
            _, binary = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Restrict characters strictly inside the structural mask (eroded slightly to skip borders)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        interior_struct = cv2.erode(roi_struct, kernel, iterations=1)
        if np.any(interior_struct > 0):
            binary = cv2.bitwise_and(binary, interior_struct)
        else:
            binary = cv2.bitwise_and(binary, roi_struct)

        char_mask[b.y1 : b.y2, b.x1 : b.x2] = binary
        return char_mask
