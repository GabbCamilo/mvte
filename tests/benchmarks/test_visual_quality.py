"""Visual quality benchmarks: PSNR preservation outside text masks and fitting rate."""

from __future__ import annotations

import math

import cv2
import numpy as np

from mvte.domain.models.page import BoundingBox, PageDocument, RegionKind
from mvte.domain.ports.vision import RawDetection
from mvte.modules.segmentation.segmenter import MaskSegmenter
from mvte.modules.text_cleaning.cleaner import SelectiveTextCleaner


def compute_psnr(img_a: np.ndarray, img_b: np.ndarray) -> float:
    mse = float(np.mean((img_a.astype(np.float64) - img_b.astype(np.float64)) ** 2))
    if mse == 0.0:
        return float("inf")
    return 20.0 * math.log10(255.0 / math.sqrt(mse))


def test_cleaning_preserves_background_outside_text_mask() -> None:
    clean_ref = np.full((300, 400, 3), 60, dtype=np.uint8)
    cv2.ellipse(clean_ref, (200, 150), (110, 60), 0, 0, 360, (255, 255, 255), -1)

    with_text = clean_ref.copy()
    cv2.putText(with_text, "TEXT", (145, 160), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 3)

    # Provide accurate ellipse polygon so structure_mask matches the balloon boundary
    angles = np.linspace(0, 2 * np.pi, 36, endpoint=False)
    poly = [(int(200 + 108 * np.cos(a)), int(150 + 58 * np.sin(a))) for a in angles]
    det = RawDetection(RegionKind.SPEECH_BALLOON, BoundingBox(90, 90, 310, 210), 0.95, polygon=poly)
    regions = MaskSegmenter().segment(with_text, [det])
    doc = PageDocument.create("memory.png", 400, 300)
    doc.regions = regions

    res = SelectiveTextCleaner().clean(with_text, doc)
    psnr = compute_psnr(clean_ref, res.cleaned_bgr)
    assert psnr >= 35.0
