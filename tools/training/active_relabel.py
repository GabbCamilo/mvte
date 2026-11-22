"""Active Learning pipeline: train specialist teacher on human-reviewed pages and re-label batch."""

from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from tools.training.prelabel_dataset import box_to_yolo_line, write_dataset_yaml
from mvte.domain.models.page import BoundingBox

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}


def find_reviewed_stems(labels_dir: Path, since_epoch: float) -> set[str]:
    """Identify label stems manually edited on or after `since_epoch`."""
    stems: set[str] = set()
    if not labels_dir.exists():
        return stems
    for txt in labels_dir.glob("*.txt"):
        if txt.stat().st_mtime >= since_epoch:
            stems.add(txt.stem)
    return stems


def build_curated_seed_dataset(
    source_dataset: Path,
    seed_dataset: Path,
    reviewed_stems: set[str],
    val_every: int = 6,
) -> tuple[int, int]:
    """Copy human-reviewed images and labels into an isolated seed dataset."""
    for split in ("train", "val"):
        (seed_dataset / "images" / split).mkdir(parents=True, exist_ok=True)
        (seed_dataset / "labels" / split).mkdir(parents=True, exist_ok=True)

    ordered = sorted(reviewed_stems)
    train_n = 0
    val_n = 0
    for idx, stem in enumerate(ordered):
        split = "val" if (idx % val_every == 0 and val_n < max(2, len(ordered) // 5)) else "train"
        img_src = _find_image_by_stem(source_dataset / "images" / "train", stem)
        lbl_src = source_dataset / "labels" / "train" / f"{stem}.txt"
        if img_src is None or not lbl_src.exists():
            continue
        shutil.copyfile(img_src, seed_dataset / "images" / split / img_src.name)
        shutil.copyfile(lbl_src, seed_dataset / "labels" / split / lbl_src.name)
        if split == "val":
            val_n += 1
        else:
            train_n += 1

    write_dataset_yaml(seed_dataset)
    return train_n, val_n


def _find_image_by_stem(img_dir: Path, stem: str) -> Path | None:
    for ext in IMAGE_EXTS:
        cand = img_dir / f"{stem}{ext}"
        if cand.exists():
            return cand
    return None


def run_active_learning(
    source_dataset: Path,
    seed_dataset: Path,
    since_iso: str,
    *,
    seed_epochs: int = 60,
    final_epochs: int = 30,
    conf_threshold: float = 0.35,
    output_onnx: Path = Path("models/mvte-custom-detector.onnx"),
) -> None:
    import torch
    from ultralytics import YOLO

    since_epoch = datetime.fromisoformat(since_iso).timestamp()
    reviewed_stems = find_reviewed_stems(source_dataset / "labels" / "train", since_epoch)
    # Preserve previously curated seed stems and any persisted manifest
    if seed_dataset.exists():
        reviewed_stems |= {
            p.stem for p in (seed_dataset / "images").rglob("*") if p.is_file()
        }
    manifest_path = source_dataset / "reviewed_stems.txt"
    if manifest_path.exists():
        reviewed_stems |= {
            line.strip() for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()
        }
    if not reviewed_stems:
        raise RuntimeError(f"No reviewed labels found since {since_iso}")
    manifest_path.write_text("\n".join(sorted(reviewed_stems)), encoding="utf-8")

    train_n, val_n = build_curated_seed_dataset(source_dataset, seed_dataset, reviewed_stems)
    print(f"Built curated seed: {len(reviewed_stems)} pages (train={train_n}, val={val_n})")

    device = 0 if torch.cuda.is_available() else "cpu"
    teacher_model = YOLO("yolo11n.pt")
    teacher_res = teacher_model.train(
        data=str((seed_dataset / "dataset.yaml").resolve()),
        epochs=seed_epochs,
        imgsz=640,
        batch=4,
        device=device,
        project="storage/training_runs",
        name="curated_teacher",
        exist_ok=True,
        workers=2,
        amp=True,
        mixup=0.15,
        mosaic=1.0,
    )
    teacher_weights = Path(teacher_res.save_dir) / "weights" / "best.pt"
    specialist = YOLO(str(teacher_weights))

    # Re-label all non-reviewed pages in source_dataset without touching human-reviewed stems
    relabeled = 0
    for split in ("train", "val"):
        img_dir = source_dataset / "images" / split
        lbl_dir = source_dataset / "labels" / split
        if not img_dir.exists():
            continue
        for img_path in sorted(img_dir.iterdir()):
            if not img_path.is_file() or img_path.suffix.lower() not in IMAGE_EXTS:
                continue
            if split == "train" and img_path.stem in reviewed_stems:
                continue
            preds = specialist.predict(
                str(img_path), imgsz=640, conf=conf_threshold, iou=0.55, device=device, verbose=False
            )[0]
            h, w = preds.orig_shape
            lines: list[str] = []
            for box, cls_t in zip(preds.boxes.xyxy.cpu().numpy(), preds.boxes.cls.cpu().numpy()):
                bbox = BoundingBox(int(box[0]), int(box[1]), max(int(box[0]) + 1, int(box[2])), max(int(box[1]) + 1, int(box[3])))
                lines.append(box_to_yolo_line(int(cls_t), bbox, w, h))
            (lbl_dir / f"{img_path.stem}.txt").write_text("\n".join(lines), encoding="utf-8")
            relabeled += 1

    print(f"Re-labeled {relabeled} non-reviewed pages (preserved {len(reviewed_stems)} human-reviewed pages).")

    # Final training on full dataset + ONNX export
    from tools.training.train_detector import train_and_export

    exported = train_and_export(
        source_dataset / "dataset.yaml",
        output_onnx,
        base_model=str(teacher_weights),
        epochs=final_epochs,
        imgsz=640,
        batch=4,
        device=device,
    )
    print(f"Final Active-Learning ONNX exported: {exported}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MVTE Active Learning Re-labeler & Trainer")
    parser.add_argument("--source-dataset", type=Path, default=Path("datasets/custom"))
    parser.add_argument("--seed-dataset", type=Path, default=Path("datasets/curated_seed"))
    parser.add_argument("--since", default="2026-11-21T21:20:00", help="ISO timestamp cutoff for human-reviewed labels")
    parser.add_argument("--seed-epochs", type=int, default=60)
    parser.add_argument("--final-epochs", type=int, default=30)
    parser.add_argument("--conf", type=float, default=0.35)
    args = parser.parse_args(argv)

    run_active_learning(
        args.source_dataset,
        args.seed_dataset,
        args.since,
        seed_epochs=args.seed_epochs,
        final_epochs=args.final_epochs,
        conf_threshold=args.conf,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
