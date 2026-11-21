"""Automated label quality audit & noise filtering for YOLO pre-labeled datasets."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from mvte.domain.models.page import BoundingBox


@dataclass
class CurationStats:
    files_scanned: int
    boxes_before: int
    boxes_after: int
    removed_tiny: int
    removed_giant: int
    removed_duplicates: int


def curate_yolo_labels(
    dataset_dir: Path | str,
    *,
    min_side: float = 0.012,
    min_area: float = 0.00025,
    max_area: float = 0.45,
    dup_iou: float = 0.70,
) -> CurationStats:
    root = Path(dataset_dir)
    files_scanned = 0
    boxes_before = 0
    boxes_after = 0
    removed_tiny = 0
    removed_giant = 0
    removed_duplicates = 0

    for split in ("train", "val"):
        lbl_dir = root / "labels" / split
        if not lbl_dir.exists():
            continue
        for txt_path in sorted(lbl_dir.glob("*.txt")):
            files_scanned += 1
            raw_lines = [l.strip() for l in txt_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            boxes_before += len(raw_lines)

            kept: list[tuple[int, float, float, float, float, BoundingBox]] = []
            for line in raw_lines:
                parts = line.split()
                if len(parts) != 5:
                    continue
                cls_id = int(parts[0])
                cx, cy, w, h = float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4])
                area = w * h
                if w < min_side or h < min_side or area < min_area:
                    removed_tiny += 1
                    continue
                if area > max_area:
                    removed_giant += 1
                    continue
                # Scale to 10000x10000 grid for exact IoU deduplication
                box = BoundingBox(
                    int((cx - w / 2) * 10000),
                    int((cy - h / 2) * 10000),
                    max(int((cx - w / 2) * 10000) + 1, int((cx + w / 2) * 10000)),
                    max(int((cy - h / 2) * 10000) + 1, int((cy + h / 2) * 10000)),
                )
                if any(k_cls == cls_id and box.iou(k_box) >= dup_iou for k_cls, _, _, _, _, k_box in kept):
                    removed_duplicates += 1
                    continue
                kept.append((cls_id, cx, cy, w, h, box))

            boxes_after += len(kept)
            out_lines = [f"{c} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}" for c, cx, cy, w, h, _ in kept]
            txt_path.write_text("\n".join(out_lines), encoding="utf-8")

    return CurationStats(
        files_scanned=files_scanned,
        boxes_before=boxes_before,
        boxes_after=boxes_after,
        removed_tiny=removed_tiny,
        removed_giant=removed_giant,
        removed_duplicates=removed_duplicates,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit and curate YOLO labels")
    parser.add_argument("--dataset-dir", type=Path, default=Path("datasets/custom"))
    args = parser.parse_args(argv)
    stats = curate_yolo_labels(args.dataset_dir)
    print(
        f"Curated {stats.files_scanned} files: {stats.boxes_before} -> {stats.boxes_after} boxes "
        f"(tiny={stats.removed_tiny}, giant={stats.removed_giant}, dups={stats.removed_duplicates})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
