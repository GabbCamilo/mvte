"""Unit tests for isolated training ingestion and YOLO pre-labeling (TRN-01, TRN-02)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import cv2
import numpy as np

from mvte.domain.models.page import BoundingBox
from tools.training.ingest_archives import ingest_from_directory
from tools.training.prelabel_dataset import box_to_yolo_line, prelabel_split


def _png_bytes(text: str) -> bytes:
    img = np.full((300, 300, 3), 255, dtype=np.uint8)
    cv2.putText(img, text, (30, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def test_trn01_ingest_archives_deduplicates_and_preserves_source(tmp_path: Path) -> None:
    src_dir = tmp_path / "mam_mock"
    src_dir.mkdir()
    cbz_path = src_dir / "ch01.cbz"
    p1 = _png_bytes("PAGE1")
    p2 = _png_bytes("PAGE2")
    with zipfile.ZipFile(cbz_path, "w") as zf:
        zf.writestr("001.png", p1)
        zf.writestr("002.png", p2)
        zf.writestr("003_dup.png", p1)  # Duplicate of 001.png

    orig_cbz_bytes = cbz_path.read_bytes()
    dataset_dir = tmp_path / "dataset"
    summary = ingest_from_directory(src_dir, dataset_dir, max_pages=10, val_ratio=0.5)

    assert cbz_path.read_bytes() == orig_cbz_bytes
    assert summary.scanned_archives == 1
    assert summary.extracted_unique == 2
    assert summary.duplicates_skipped == 1
    assert (summary.train_count + summary.val_count) == 2


def test_trn02_yolo_line_normalization_and_prelabel_export(tmp_path: Path) -> None:
    line = box_to_yolo_line(2, BoundingBox(50, 100, 150, 200), img_w=200, img_h=400)
    parts = [float(x) for x in line.split()]
    assert int(parts[0]) == 2
    assert abs(parts[1] - 0.5) < 1e-5
    assert abs(parts[2] - 0.375) < 1e-5
    assert abs(parts[3] - 0.5) < 1e-5
    assert abs(parts[4] - 0.25) < 1e-5

    model_path = Path("C:/Users/Gabriel/Documents/mvte/models/comic-text-and-bubble-detector_int8.onnx")
    if model_path.exists():
        ds = tmp_path / "ds"
        (ds / "images" / "train").mkdir(parents=True)
        (ds / "images" / "train" / "sample.png").write_bytes(_png_bytes("HELLO!"))
        count = prelabel_split(ds, model_path, use_rapidocr_teacher=True)
        assert count == 1
        assert (ds / "dataset.yaml").exists()
        assert (ds / "labels" / "train" / "sample.txt").exists()
