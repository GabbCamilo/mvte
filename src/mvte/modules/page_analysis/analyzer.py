"""Global page analysis: panel detection and RTL/LTR reading order."""

from __future__ import annotations

import uuid

import cv2
import numpy as np

from mvte.domain.models.page import BoundingBox, Panel, ReadingDirection


class ContourPageAnalyzer:
    """Detects comic/manga panels via gutter-aware contour analysis and computes reading order."""

    def __init__(self, min_panel_area_ratio: float = 0.03) -> None:
        self.min_panel_area_ratio = min_panel_area_ratio

    def analyze(
        self, image_bgr: np.ndarray, direction: ReadingDirection = ReadingDirection.RTL
    ) -> list[Panel]:
        height, width = image_bgr.shape[:2]
        page_area = float(width * height)
        if page_area == 0:
            return []

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        # Invert so dark panel borders/contents become foreground against white gutters.
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidate_boxes: list[tuple[BoundingBox, list[tuple[int, int]]]] = []

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area_ratio = (w * h) / page_area
            if area_ratio < self.min_panel_area_ratio:
                continue
            epsilon = 0.01 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            polygon = [(int(pt[0][0]), int(pt[0][1])) for pt in approx]
            candidate_boxes.append((BoundingBox(x, y, x + w, y + h), polygon))

        if not candidate_boxes:
            full_box = BoundingBox(0, 0, width, height)
            return [
                Panel(
                    id=str(uuid.uuid4()),
                    bbox=full_box,
                    reading_order=0,
                    polygon=[(0, 0), (width, 0), (width, height), (0, height)],
                )
            ]

        ordered = self._sort_reading_order(candidate_boxes, direction)
        return [
            Panel(
                id=str(uuid.uuid4()),
                bbox=bbox,
                reading_order=idx,
                polygon=polygon,
            )
            for idx, (bbox, polygon) in enumerate(ordered)
        ]

    @staticmethod
    def _sort_reading_order(
        items: list[tuple[BoundingBox, list[tuple[int, int]]]],
        direction: ReadingDirection,
    ) -> list[tuple[BoundingBox, list[tuple[int, int]]]]:
        """Group panels into visual rows (vertical overlap) and sort RTL or LTR within rows."""
        sorted_by_top = sorted(items, key=lambda item: item[0].y1)
        rows: list[list[tuple[BoundingBox, list[tuple[int, int]]]]] = []

        for item in sorted_by_top:
            bbox = item[0]
            placed = False
            for row in rows:
                row_y1 = min(r[0].y1 for r in row)
                row_y2 = max(r[0].y2 for r in row)
                overlap = max(0, min(bbox.y2, row_y2) - max(bbox.y1, row_y1))
                min_h = min(bbox.height, row_y2 - row_y1)
                if min_h > 0 and (overlap / min_h) >= 0.4:
                    row.append(item)
                    placed = True
                    break
            if not placed:
                rows.append([item])

        ordered: list[tuple[BoundingBox, list[tuple[int, int]]]] = []
        reverse_x = direction == ReadingDirection.RTL
        for row in rows:
            row.sort(key=lambda item: item[0].x1, reverse=reverse_x)
            ordered.extend(row)
        return ordered
