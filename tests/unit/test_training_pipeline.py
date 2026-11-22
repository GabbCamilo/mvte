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


def test_yolo_label_reviewer_roundtrip(tmp_path: Path) -> None:
    from tools.training.label_reviewer import YoloBox, load_yolo_boxes, save_yolo_boxes

    lbl = tmp_path / "page.txt"
    boxes = [YoloBox(0, 10.0, 20.0, 110.0, 120.0), YoloBox(2, 200.0, 50.0, 300.0, 250.0)]
    save_yolo_boxes(lbl, boxes, img_w=400, img_h=400)
    loaded = load_yolo_boxes(lbl, img_w=400, img_h=400)
    assert len(loaded) == 2
    assert loaded[0].class_id == 0
    assert loaded[1].class_id == 2
    assert abs(loaded[0].x1 - 10.0) < 1.0


def test_active_learning_seed_builder_preserves_reviewed(tmp_path: Path) -> None:
    import os
    from tools.training.active_relabel import build_curated_seed_dataset, find_reviewed_stems

    src = tmp_path / "custom"
    (src / "images" / "train").mkdir(parents=True)
    (src / "labels" / "train").mkdir(parents=True)

    old_lbl = src / "labels" / "train" / "old.txt"
    new_lbl = src / "labels" / "train" / "reviewed1.txt"
    (src / "images" / "train" / "old.png").write_bytes(_png_bytes("OLD"))
    (src / "images" / "train" / "reviewed1.png").write_bytes(_png_bytes("NEW"))
    old_lbl.write_text("0 0.5 0.5 0.2 0.2", encoding="utf-8")
    new_lbl.write_text("2 0.5 0.5 0.3 0.3", encoding="utf-8")

    os.utime(old_lbl, (1000.0, 1000.0))
    os.utime(new_lbl, (5000.0, 5000.0))

    stems = find_reviewed_stems(src / "labels" / "train", since_epoch=3000.0)
    assert stems == {"reviewed1"}

    seed = tmp_path / "seed"
    train_n, val_n = build_curated_seed_dataset(src, seed, stems)
    assert (train_n + val_n) == 1
    assert (seed / "dataset.yaml").exists()


def test_yolo11_onnx_decoder_and_default_resolver() -> None:
    from mvte.domain.models.page import RegionKind
    from mvte.modules.visual_detection.detector import Yolo11OnnxDetector, resolve_default_detector

    det = Yolo11OnnxDetector("models/mvte-custom-detector.onnx", conf_threshold=0.5)
    # Synthetic (1, 7, 2) output: [cx, cy, w, h, s0, s1, s2]
    fake_out = np.zeros((1, 7, 2), dtype=np.float32)
    fake_out[0, :4, 0] = [320.0, 320.0, 160.0, 80.0]
    fake_out[0, 4, 0] = 0.92  # class 0: speech_balloon
    fake_out[0, :4, 1] = [100.0, 100.0, 40.0, 20.0]
    fake_out[0, 6, 1] = 0.20  # below threshold

    results = det._decode_outputs(fake_out, orig_w=640, orig_h=640)
    assert len(results) == 1
    assert results[0].kind == RegionKind.SPEECH_BALLOON
    assert results[0].confidence > 0.9

    default_det = resolve_default_detector()
    assert default_det.name.startswith(("hybrid", "yolo11_onnx", "rtdetr_onnx", "morphological"))


def test_hyb01_hyb02_hybrid_ensemble_and_ctd_segmenter() -> None:
    from mvte.domain.models.page import RegionKind
    from mvte.domain.ports.vision import RawDetection
    from mvte.modules.segmentation.segmenter import resolve_default_segmenter
    from mvte.modules.visual_detection.detector import HybridEnsembleDetector

    class Prim:
        name = "prim"

        def detect(self, img):
            return [RawDetection(RegionKind.SPEECH_BALLOON, BoundingBox(10, 10, 100, 100), 0.9)]

        def unload(self):
            return None

    class Sec:
        name = "sec"

        def detect(self, img):
            return [
                RawDetection(RegionKind.FREE_TEXT, BoundingBox(12, 12, 98, 98), 0.8),  # overlaps
                RawDetection(RegionKind.FREE_TEXT, BoundingBox(200, 200, 280, 260), 0.85),  # unique
            ]

        def unload(self):
            return None

    ens = HybridEnsembleDetector(Prim(), Sec(), complement_iou_threshold=0.35)
    img = np.full((300, 300, 3), 255, dtype=np.uint8)
    dets = ens.detect(img)
    assert len(dets) == 2
    assert dets[0].kind == RegionKind.SPEECH_BALLOON
    assert dets[1].kind == RegionKind.FREE_TEXT
    ens.unload()

    seg = resolve_default_segmenter()
    assert seg is not None
