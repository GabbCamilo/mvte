"""Detection (Precision/Recall/F1) and segmentation (IoU/Dice) metric benchmarks."""

from __future__ import annotations

import numpy as np

from mvte.domain.models.page import BoundingBox
from mvte.modules.segmentation.segmenter import MaskSegmenter
from mvte.domain.ports.vision import RawDetection
from mvte.domain.models.page import RegionKind


def compute_detection_metrics(
    predicted: list[BoundingBox], ground_truth: list[BoundingBox], iou_threshold: float = 0.5
) -> tuple[float, float, float]:
    matched_gt: set[int] = set()
    tp = 0
    for pred in predicted:
        for idx, gt in enumerate(ground_truth):
            if idx not in matched_gt and pred.iou(gt) >= iou_threshold:
                matched_gt.add(idx)
                tp += 1
                break
    fp = len(predicted) - tp
    fn = len(ground_truth) - tp
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return precision, recall, f1


def compute_mask_iou_dice(pred_mask: np.ndarray, gt_mask: np.ndarray) -> tuple[float, float]:
    p = pred_mask > 0
    g = gt_mask > 0
    inter = float(np.logical_and(p, g).sum())
    union = float(np.logical_or(p, g).sum())
    denom = float(p.sum() + g.sum())
    iou = inter / union if union > 0 else 0.0
    dice = (2.0 * inter) / denom if denom > 0 else 0.0
    return iou, dice


def test_detection_and_segmentation_metrics() -> None:
    gt_boxes = [BoundingBox(50, 50, 200, 150), BoundingBox(300, 200, 500, 340)]
    pred_boxes = [BoundingBox(54, 52, 198, 148), BoundingBox(305, 205, 495, 338)]
    precision, recall, f1 = compute_detection_metrics(pred_boxes, gt_boxes)
    assert precision == 1.0
    assert recall == 1.0
    assert f1 == 1.0

    img = np.full((400, 600, 3), 255, dtype=np.uint8)
    det = RawDetection(RegionKind.NARRATION_BOX, gt_boxes[0], 0.95)
    region = MaskSegmenter().segment(img, [det])[0]
    gt_mask = np.zeros((400, 600), dtype=np.uint8)
    gt_mask[50:150, 50:200] = 255
    iou, dice = compute_mask_iou_dice(region.structure_mask.data, gt_mask)
    assert iou >= 0.95
    assert dice >= 0.97
