"""Global page analysis: recursive gutter-splitting panel detection and RTL/LTR reading order."""

from __future__ import annotations

import uuid

import cv2
import numpy as np

from mvte.domain.models.page import BoundingBox, Panel, ReadingDirection


class ContourPageAnalyzer:
    """Detects comic/manga panels using recursive XY-cut gutter splitting with contour fallback."""

    def __init__(
        self,
        min_panel_area_ratio: float = 0.03,
        gutter_white_thresh: int = 232,
        min_gutter_run: int = 4,
    ) -> None:
        self.min_panel_area_ratio = min_panel_area_ratio
        self.gutter_white_thresh = gutter_white_thresh
        self.min_gutter_run = min_gutter_run

    def analyze(
        self, image_bgr: np.ndarray, direction: ReadingDirection = ReadingDirection.RTL
    ) -> list[Panel]:
        height, width = image_bgr.shape[:2]
        page_area = float(width * height)
        if page_area == 0:
            return []

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        raw_boxes = self._recursive_xy_cut(gray, 0, 0, width, height, page_area)

        # Fallback to external contours if XY-cut produced only 1 full-page box
        if len(raw_boxes) <= 1:
            contour_boxes = self._contour_panels(gray, page_area)
            if len(contour_boxes) > len(raw_boxes):
                raw_boxes = contour_boxes

        if not raw_boxes:
            full_box = BoundingBox(0, 0, width, height)
            return [
                Panel(
                    id=str(uuid.uuid4()),
                    bbox=full_box,
                    reading_order=0,
                    polygon=[(0, 0), (width, 0), (width, height), (0, height)],
                )
            ]

        ordered = self._sort_reading_order(raw_boxes, direction)
        return [
            Panel(
                id=str(uuid.uuid4()),
                bbox=bbox,
                reading_order=idx,
                polygon=polygon,
            )
            for idx, (bbox, polygon) in enumerate(ordered)
        ]

    def _recursive_xy_cut(
        self,
        gray: np.ndarray,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        page_area: float,
        depth: int = 0,
    ) -> list[tuple[BoundingBox, list[tuple[int, int]]]]:
        w, h = x2 - x1, y2 - y1
        if w < 40 or h < 40 or depth > 6:
            return []

        roi = gray[y1:y2, x1:x2]
        # Trim outer white margin around current region
        non_white = roi < self.gutter_white_thresh
        ys, xs = np.where(non_white)
        if xs.size == 0 or ys.size == 0:
            return []

        tx1, tx2 = x1 + int(xs.min()), x1 + int(xs.max()) + 1
        ty1, ty2 = y1 + int(ys.min()), y1 + int(ys.max()) + 1
        sub = gray[ty1:ty2, tx1:tx2]
        sh, sw = sub.shape[:2]

        # Look for horizontal gutter (a row band that is >= 92% white)
        row_white_ratio = np.mean(sub >= self.gutter_white_thresh, axis=1)
        h_cuts = self._find_gutter_cuts(row_white_ratio, min_ratio=0.92, min_len=self.min_gutter_run)
        if h_cuts:
            mid = h_cuts[len(h_cuts) // 2]
            top = self._recursive_xy_cut(gray, tx1, ty1, tx2, ty1 + mid[0], page_area, depth + 1)
            bot = self._recursive_xy_cut(gray, tx1, ty1 + mid[1], tx2, ty2, page_area, depth + 1)
            if top and bot:
                return top + bot

        # Look for vertical gutter (a column band that is >= 92% white)
        col_white_ratio = np.mean(sub >= self.gutter_white_thresh, axis=0)
        v_cuts = self._find_gutter_cuts(col_white_ratio, min_ratio=0.92, min_len=self.min_gutter_run)
        if v_cuts:
            mid = v_cuts[len(v_cuts) // 2]
            left = self._recursive_xy_cut(gray, tx1, ty1, tx1 + mid[0], ty2, page_area, depth + 1)
            right = self._recursive_xy_cut(gray, tx1 + mid[1], ty1, tx2, ty2, page_area, depth + 1)
            if left and right:
                return left + right

        if ((tx2 - tx1) * (ty2 - ty1)) / page_area < self.min_panel_area_ratio:
            return []
        bbox = BoundingBox(tx1, ty1, tx2, ty2)
        poly = [(tx1, ty1), (tx2, ty1), (tx2, ty2), (tx1, ty2)]
        return [(bbox, poly)]

    @staticmethod
    def _find_gutter_cuts(
        ratios: np.ndarray, min_ratio: float, min_len: int
    ) -> list[tuple[int, int]]:
        n = len(ratios)
        # Ignore outer 4% border
        margin = max(2, int(n * 0.04))
        cuts: list[tuple[int, int]] = []
        start: int | None = None
        for i in range(margin, n - margin):
            if ratios[i] >= min_ratio:
                if start is None:
                    start = i
            else:
                if start is not None and (i - start) >= min_len:
                    cuts.append((start, i))
                start = None
        if start is not None and (n - margin - start) >= min_len:
            cuts.append((start, n - margin))
        return cuts

    def _contour_panels(
        self, gray: np.ndarray, page_area: float
    ) -> list[tuple[BoundingBox, list[tuple[int, int]]]]:
        _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes: list[tuple[BoundingBox, list[tuple[int, int]]]] = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if (w * h) / page_area < self.min_panel_area_ratio:
                continue
            epsilon = 0.01 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            polygon = [(int(pt[0][0]), int(pt[0][1])) for pt in approx]
            boxes.append((BoundingBox(x, y, x + w, y + h), polygon))
        return boxes

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
