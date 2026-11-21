"""Isolated detector fine-tuning and ONNX export (designed for 4 GB VRAM GTX 1650)."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def train_and_export(
    dataset_yaml: Path | str,
    output_onnx: Path | str,
    *,
    base_model: str = "yolo11n.pt",
    epochs: int = 25,
    imgsz: int = 640,
    batch: int = 4,
    device: str | int | None = None,
) -> Path:
    import torch
    from ultralytics import YOLO

    resolved_device = device if device is not None else (0 if torch.cuda.is_available() else "cpu")
    model = YOLO(base_model)
    results = model.train(
        data=str(Path(dataset_yaml).resolve()),
        epochs=epochs,
        imgsz=imgsz,
        batch=batch,
        device=resolved_device,
        project="storage/training_runs",
        name="mvte_detector",
        exist_ok=True,
        workers=2,
        amp=True,
    )

    best_pt = Path(results.save_dir) / "weights" / "best.pt"
    best_model = YOLO(str(best_pt))
    exported = Path(best_model.export(format="onnx", imgsz=imgsz, simplify=True))

    dest = Path(output_onnx)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(exported, dest)
    return dest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MVTE Isolated Detector Trainer & ONNX Exporter")
    parser.add_argument("--data", type=Path, default=Path("datasets/custom/dataset.yaml"))
    parser.add_argument("--out", type=Path, default=Path("models/mvte-custom-detector.onnx"))
    parser.add_argument("--base-model", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=4)
    args = parser.parse_args(argv)

    out_path = train_and_export(
        args.data,
        args.out,
        base_model=args.base_model,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
    )
    print(f"Exported custom ONNX detector: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
