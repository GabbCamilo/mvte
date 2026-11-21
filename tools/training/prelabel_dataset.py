"""Teacher-ensemble pre-labeling into normalized YOLO format for human curation & training."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from mvte.domain.models.page import BoundingBox, RegionKind
from mvte.modules.visual_detection.detector import RtDetrOnnxDetector


CLASS_NAMES = {
    0: "speech_balloon",
    1: "text_bubble",
    2: "text_free",
}


def box_to_yolo_line(class_id: int, bbox: BoundingBox, img_w: int, img_h: int) -> str:
    cx = ((bbox.x1 + bbox.x2) / 2.0) / float(img_w)
    cy = ((bbox.y1 + bbox.y2) / 2.0) / float(img_h)
    bw = bbox.width / float(img_w)
    bh = bbox.height / float(img_h)
    cx = min(1.0, max(0.0, cx))
    cy = min(1.0, max(0.0, cy))
    bw = min(1.0, max(0.0, bw))
    bh = min(1.0, max(0.0, bh))
    return f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}"


def write_dataset_yaml(dataset_dir: Path) -> Path:
    yaml_path = dataset_dir / "dataset.yaml"
    content = (
        f"path: {dataset_dir.resolve().as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "names:\n"
        "  0: speech_balloon\n"
        "  1: text_bubble\n"
        "  2: text_free\n"
    )
    yaml_path.write_text(content, encoding="utf-8")
    return yaml_path


def prelabel_split(
    dataset_dir: Path | str,
    model_path: Path | str,
    *,
    conf_threshold: float = 0.45,
    use_rapidocr_teacher: bool = True,
) -> int:
    """Generate YOLO .txt label files for train and val splits using local ONNX teachers."""
    root = Path(dataset_dir)
    detector = RtDetrOnnxDetector(model_path=model_path, conf_threshold=conf_threshold)

    ocr_teacher = None
    if use_rapidocr_teacher:
        try:
            from rapidocr_onnxruntime import RapidOCR

            ocr_teacher = RapidOCR()
        except ImportError:
            ocr_teacher = None

    labeled_count = 0
    try:
        for split in ("train", "val"):
            img_dir = root / "images" / split
            lbl_dir = root / "labels" / split
            if not img_dir.exists():
                continue
            lbl_dir.mkdir(parents=True, exist_ok=True)

            for img_path in sorted(img_dir.iterdir()):
                if not img_path.is_file():
                    continue
                img_bgr = cv2.imread(str(img_path))
                if img_bgr is None:
                    continue
                h, w = img_bgr.shape[:2]
                detections = detector.detect(img_bgr)

                entries: list[tuple[int, BoundingBox]] = []
                for det in detections:
                    cls_id = 0 if det.kind == RegionKind.SPEECH_BALLOON else 2
                    entries.append((cls_id, det.bbox))

                if ocr_teacher is not None:
                    ocr_res, _ = ocr_teacher(img_bgr)
                    for item in ocr_res or []:
                        poly = item[0]
                        xs = [int(round(p[0])) for p in poly]
                        ys = [int(round(p[1])) for p in poly]
                        ocr_box = BoundingBox(
                            max(0, min(xs)),
                            max(0, min(ys)),
                            min(w, max(max(xs), min(xs) + 1)),
                            min(h, max(max(ys), min(ys) + 1)),
                        )
                        # Only add OCR box as text_free if not already heavily covered by detector
                        if not any(ocr_box.iou(b) >= 0.4 for _, b in entries):
                            entries.append((2, ocr_box))

                lines = [box_to_yolo_line(cid, box, w, h) for cid, box in entries]
                (lbl_dir / f"{img_path.stem}.txt").write_text("\n".join(lines), encoding="utf-8")
                labeled_count += 1
    finally:
        detector.unload()

    write_dataset_yaml(root)
    return labeled_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MVTE Teacher-Ensemble YOLO Pre-Labeler")
    parser.add_argument("--dataset-dir", type=Path, default=Path("datasets/custom"))
    parser.add_argument(
        "--model-path",
        type=Path,
        default=Path("models/comic-text-and-bubble-detector_int8.onnx"),
    )
    parser.add_argument("--conf", type=float, default=0.45)
    parser.add_argument("--no-rapidocr", action="store_true")
    args = parser.parse_args(argv)

    count = prelabel_split(
        args.dataset_dir,
        args.model_path,
        conf_threshold=args.conf,
        use_rapidocr_teacher=not args.no_rapidocr,
    )
    print(f"Pre-labeled {count} images -> {args.dataset_dir / 'dataset.yaml'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
