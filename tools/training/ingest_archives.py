"""Read-only archive (.cbz/.zip) and image ingestion for MVTE detector training."""

from __future__ import annotations

import argparse
import hashlib
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
ARCHIVE_EXTENSIONS = {".cbz", ".zip"}


@dataclass
class IngestSummary:
    scanned_archives: int
    extracted_unique: int
    duplicates_skipped: int
    train_count: int
    val_count: int


def _is_valid_image_bytes(raw: bytes) -> bool:
    try:
        with Image.open(io.BytesIO(raw)) as img:
            img.verify()
        return True
    except (UnidentifiedImageError, OSError, ValueError):
        return False


def ingest_from_directory(
    source_dir: Path | str,
    dataset_dir: Path | str,
    *,
    max_pages: int | None = None,
    val_ratio: float = 0.15,
) -> IngestSummary:
    """Extract unique pages from .cbz/.zip and loose images without modifying source_dir."""
    src = Path(source_dir)
    dst = Path(dataset_dir)
    train_dir = dst / "images" / "train"
    val_dir = dst / "images" / "val"
    train_dir.mkdir(parents=True, exist_ok=True)
    val_dir.mkdir(parents=True, exist_ok=True)

    seen_hashes: set[str] = set()
    scanned_archives = 0
    extracted = 0
    duplicates = 0
    train_count = 0
    val_count = 0

    def _save_candidate(raw: bytes, ext: str) -> bool:
        nonlocal extracted, duplicates, train_count, val_count
        if max_pages is not None and extracted >= max_pages:
            return False
        digest = hashlib.sha256(raw).hexdigest()
        if digest in seen_hashes:
            duplicates += 1
            return True
        if not _is_valid_image_bytes(raw):
            return True
        seen_hashes.add(digest)

        # Deterministic split based on hash prefix
        is_val = (int(digest[:4], 16) / 65535.0) < val_ratio
        target_dir = val_dir if is_val else train_dir
        out_path = target_dir / f"{digest[:16]}{ext.lower()}"
        out_path.write_bytes(raw)
        extracted += 1
        if is_val:
            val_count += 1
        else:
            train_count += 1
        return True

    for item in sorted(src.rglob("*")):
        if max_pages is not None and extracted >= max_pages:
            break
        if not item.is_file():
            continue
        suffix = item.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            _save_candidate(item.read_bytes(), suffix)
        elif suffix in ARCHIVE_EXTENSIONS:
            scanned_archives += 1
            try:
                with zipfile.ZipFile(item, "r") as zf:
                    for member in sorted(zf.namelist()):
                        if max_pages is not None and extracted >= max_pages:
                            break
                        m_suffix = Path(member).suffix.lower()
                        if m_suffix not in IMAGE_EXTENSIONS:
                            continue
                        raw = zf.read(member)
                        _save_candidate(raw, m_suffix)
            except (zipfile.BadZipFile, OSError):
                continue

    return IngestSummary(
        scanned_archives=scanned_archives,
        extracted_unique=extracted,
        duplicates_skipped=duplicates,
        train_count=train_count,
        val_count=val_count,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MVTE Read-Only CBZ/ZIP Dataset Ingestor")
    parser.add_argument("source_dir", type=Path, help="Source library directory (read-only)")
    parser.add_argument(
        "--dataset-dir",
        type=Path,
        default=Path("datasets/custom"),
        help="Destination YOLO dataset directory",
    )
    parser.add_argument("--max-pages", type=int, default=500, help="Maximum unique pages to extract")
    parser.add_argument("--val-ratio", type=float, default=0.15, help="Validation split ratio")
    args = parser.parse_args(argv)

    summary = ingest_from_directory(
        args.source_dir,
        args.dataset_dir,
        max_pages=args.max_pages,
        val_ratio=args.val_ratio,
    )
    print(
        f"Archives scanned: {summary.scanned_archives} | Unique pages: {summary.extracted_unique} "
        f"(train={summary.train_count}, val={summary.val_count}) | Duplicates skipped: {summary.duplicates_skipped}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
