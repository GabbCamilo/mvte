"""Replaceable visual structure detectors and registry."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import cv2
import numpy as np

from mvte.domain.models.page import BoundingBox, RegionKind
from mvte.domain.ports.vision import RawDetection, VisualDetectorPort
from mvte.infrastructure.inference.onnx_runner import OnnxSessionWrapper


class MorphologicalBalloonDetector:
    """Baseline local CPU detector for balloons, narration boxes, and text-like regions.

    Requires no external model weights; useful as a deterministic fallback and test baseline.
    """

    name = "morphological_baseline"

    def __init__(self, min_area: int = 900, max_area_ratio: float = 0.35) -> None:
        self.min_area = min_area
        self.max_area_ratio = max_area_ratio

    def detect(self, image_bgr: np.ndarray) -> list[RawDetection]:
        height, width = image_bgr.shape[:2]
        page_area = float(width * height)
        if page_area == 0:
            return []

        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        # Bright enclosed interiors (speech balloons / light narration boxes)
        _, bright = cv2.threshold(gray, 225, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(bright, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)

        detections: list[RawDetection] = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            box_area = w * h
            if box_area < self.min_area or (box_area / page_area) > self.max_area_ratio:
                continue
            if w < 24 or h < 24:
                continue

            roi_gray = gray[y : y + h, x : x + w]
            # Must contain dark ink pixels (text) inside a bright region
            dark_ratio = float(np.mean(roi_gray < 140))
            if dark_ratio < 0.015 or dark_ratio > 0.65:
                continue

            cnt_area = cv2.contourArea(cnt)
            rectangularity = cnt_area / float(box_area) if box_area > 0 else 0.0
            kind = RegionKind.NARRATION_BOX if rectangularity > 0.88 else RegionKind.SPEECH_BALLOON

            epsilon = 0.015 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            polygon = [(int(pt[0][0]), int(pt[0][1])) for pt in approx]

            detections.append(
                RawDetection(
                    kind=kind,
                    bbox=BoundingBox(x, y, x + w, y + h),
                    confidence=min(0.95, 0.55 + dark_ratio),
                    polygon=polygon,
                )
            )

        return self._deduplicate_nms(detections, iou_threshold=0.6)

    def unload(self) -> None:
        return None

    @staticmethod
    def _deduplicate_nms(
        detections: list[RawDetection], iou_threshold: float
    ) -> list[RawDetection]:
        ordered = sorted(detections, key=lambda d: d.confidence, reverse=True)
        kept: list[RawDetection] = []
        for det in ordered:
            if any(det.bbox.iou(k.bbox) >= iou_threshold for k in kept):
                continue
            kept.append(det)
        return kept


class OnnxVisualDetector:
    """Adapter for replaceable ONNX object/region detection models (e.g. YOLO-ONNX)."""

    def __init__(
        self,
        model_path: Path | str,
        class_map: dict[int, RegionKind] | None = None,
        input_size: int = 640,
        conf_threshold: float = 0.35,
        prefer_gpu: bool = True,
    ) -> None:
        self.name = f"onnx:{Path(model_path).stem}"
        self.session = OnnxSessionWrapper(model_path, prefer_gpu=prefer_gpu)
        self.class_map = class_map or {
            0: RegionKind.SPEECH_BALLOON,
            1: RegionKind.THOUGHT_BALLOON,
            2: RegionKind.NARRATION_BOX,
            3: RegionKind.SFX,
            4: RegionKind.FREE_TEXT,
        }
        self.input_size = input_size
        self.conf_threshold = conf_threshold

    def detect(self, image_bgr: np.ndarray) -> list[RawDetection]:
        self.session.load()
        orig_h, orig_w = image_bgr.shape[:2]
        resized = cv2.resize(image_bgr, (self.input_size, self.input_size))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        chw = np.transpose(rgb, (2, 0, 1))[None, ...]

        input_name = self.session._session.get_inputs()[0].name
        outputs = self.session.run({input_name: chw})
        preds = np.squeeze(outputs[0])
        if preds.ndim != 2 or preds.shape[1] < 6:
            return []

        scale_x = orig_w / float(self.input_size)
        scale_y = orig_h / float(self.input_size)
        detections: list[RawDetection] = []
        for row in preds:
            x1, y1, x2, y2, conf, cls_id = row[:6]
            if float(conf) < self.conf_threshold:
                continue
            bx1 = max(0, min(orig_w, int(x1 * scale_x)))
            by1 = max(0, min(orig_h, int(y1 * scale_y)))
            bx2 = max(bx1 + 1, min(orig_w, int(x2 * scale_x)))
            by2 = max(by1 + 1, min(orig_h, int(y2 * scale_y)))
            kind = self.class_map.get(int(cls_id), RegionKind.UNKNOWN)
            detections.append(
                RawDetection(
                    kind=kind,
                    bbox=BoundingBox(bx1, by1, bx2, by2),
                    confidence=float(conf),
                )
            )
        return detections

    def unload(self) -> None:
        self.session.unload()


class DetectorRegistry:
    """Registry allowing runtime replacement of visual detection backends."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], VisualDetectorPort]] = {}

    def register(self, name: str, factory: Callable[[], VisualDetectorPort]) -> None:
        self._factories[name] = factory

    def create(self, name: str) -> VisualDetectorPort:
        if name not in self._factories:
            available = ", ".join(sorted(self._factories))
            raise KeyError(f"Unknown detector '{name}'. Available: {available}")
        return self._factories[name]()

    def list_backends(self) -> list[str]:
        return sorted(self._factories)
