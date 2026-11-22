"""Comparative benchmark of MVTE detectors on real validation pages."""

from __future__ import annotations

import argparse
import time
from collections import Counter
from pathlib import Path

import cv2

from mvte.modules.visual_detection.detector import (
    HybridEnsembleDetector,
    RtDetrOnnxDetector,
    Yolo11OnnxDetector,
)


def run_benchmark(val_dir: Path, max_images: int = 20) -> None:
    images = sorted(
        p for p in val_dir.iterdir() if p.is_file() and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
    )[:max_images]
    if not images:
        print("No validation images found.")
        return

    yolo = Yolo11OnnxDetector("models/mvte-custom-detector.onnx")
    rtdetr = RtDetrOnnxDetector("models/comic-text-and-bubble-detector_int8.onnx")
    hybrid = HybridEnsembleDetector(
        Yolo11OnnxDetector("models/mvte-custom-detector.onnx"),
        RtDetrOnnxDetector("models/comic-text-and-bubble-detector_int8.onnx"),
    )

    for det in (yolo, rtdetr, hybrid):
        counts: Counter[str] = Counter()
        t0 = time.perf_counter()
        try:
            for img_path in images:
                img = cv2.imread(str(img_path))
                if img is None:
                    continue
                for d in det.detect(img):
                    counts[d.kind.value] += 1
        finally:
            det.unload()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        avg_ms = elapsed_ms / len(images)
        print(f"{det.name:55s} | avg={avg_ms:6.1f} ms/page | counts={dict(counts)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark MVTE detectors")
    parser.add_argument("--val-dir", type=Path, default=Path("datasets/custom/images/val"))
    parser.add_argument("--max-images", type=int, default=20)
    args = parser.parse_args()
    run_benchmark(args.val_dir, args.max_images)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
