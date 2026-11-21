"""CLI entrypoint for MVTE Phase 1 page analysis and overlay inspection."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

from mvte.application.use_cases.analyze_page import AnalyzePageUseCase
from mvte.application.use_cases.transcribe_page import TranscribePageUseCase
from mvte.domain.models.page import PageDocument, ReadingDirection
from mvte.infrastructure.storage.document_store import DocumentStore, load_image_lossless
from mvte.modules.linguistic_analysis.reconstructor import SentenceReconstructor
from mvte.modules.ocr.backends import MangaOcrAdapter, OcrRegistry, RapidOcrAdapter
from mvte.modules.page_analysis.analyzer import ContourPageAnalyzer
from mvte.modules.segmentation.segmenter import MaskSegmenter
from mvte.modules.text_association.associator import SpatialRegionAssociator
from mvte.modules.visual_detection.detector import (
    DetectorRegistry,
    MorphologicalBalloonDetector,
    OnnxVisualDetector,
)


def render_debug_overlay(image_bgr: np.ndarray, document: PageDocument) -> np.ndarray:
    """Draw panels, reading order, structural masks, and character masks onto a copy."""
    canvas = image_bgr.copy()
    overlay = image_bgr.copy()

    for panel in document.panels:
        b = panel.bbox
        cv2.rectangle(canvas, (b.x1, b.y1), (b.x2, b.y2), (255, 160, 0), 2)
        cv2.putText(
            canvas,
            f"P{panel.reading_order}",
            (b.x1 + 6, b.y1 + 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 160, 0),
            2,
        )

    for region in document.regions:
        if region.structure_mask and region.structure_mask.data is not None:
            overlay[region.structure_mask.data > 0] = (0, 200, 0)
        if region.character_mask and region.character_mask.data is not None:
            overlay[region.character_mask.data > 0] = (0, 0, 255)
        b = region.bbox
        cv2.rectangle(canvas, (b.x1, b.y1), (b.x2, b.y2), (0, 180, 0), 2)
        cv2.putText(
            canvas,
            f"{region.kind.value} ({region.confidence:.2f})",
            (b.x1, max(18, b.y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 180, 0),
            1,
        )

    return cv2.addWeighted(overlay, 0.3, canvas, 0.7, 0)


def build_default_registry(onnx_model: str | None = None) -> DetectorRegistry:
    registry = DetectorRegistry()
    registry.register("morphological", MorphologicalBalloonDetector)
    if onnx_model:
        registry.register("onnx", lambda: OnnxVisualDetector(onnx_model))
    return registry


def build_default_ocr_registry() -> OcrRegistry:
    registry = OcrRegistry()
    registry.register("rapidocr", RapidOcrAdapter)
    registry.register("manga_ocr", MangaOcrAdapter)
    return registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MVTE Phase 1 — Global Page Reader")
    parser.add_argument("image", type=Path, help="Path to manga/comic page image")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("storage/runs"),
        help="Workspace directory for PageDocument JSON, masks, and overlays",
    )
    parser.add_argument(
        "--direction",
        choices=["rtl", "ltr"],
        default="rtl",
        help="Reading direction (rtl=manga, ltr=western)",
    )
    parser.add_argument(
        "--detector",
        default="morphological",
        help="Detector backend name (default: morphological)",
    )
    parser.add_argument(
        "--onnx-model",
        type=str,
        default=None,
        help="Optional path to ONNX detection model (activates 'onnx' backend)",
    )
    parser.add_argument(
        "--save-overlay",
        action="store_true",
        help="Save a visual overlay PNG for inspection",
    )
    parser.add_argument(
        "--transcribe",
        action="store_true",
        help="Run Phase 2 OCR and linguistic reconstruction",
    )
    parser.add_argument(
        "--ocr-backend",
        default="rapidocr",
        help="OCR backend name (default: rapidocr)",
    )
    args = parser.parse_args(argv)

    registry = build_default_registry(args.onnx_model)
    detector = registry.create(args.detector)
    store = DocumentStore(args.output_dir)
    use_case = AnalyzePageUseCase(
        page_analyzer=ContourPageAnalyzer(),
        detector=detector,
        segmenter=MaskSegmenter(),
        associator=SpatialRegionAssociator(),
        store=store,
    )

    doc = use_case.execute(
        args.image,
        reading_direction=ReadingDirection(args.direction),
        persist=True,
    )

    if args.transcribe:
        ocr_backend = build_default_ocr_registry().create(args.ocr_backend)
        transcribe_uc = TranscribePageUseCase(
            ocr_backend=ocr_backend,
            reconstructor=SentenceReconstructor(),
            store=store,
        )
        doc = transcribe_uc.execute(doc, persist=True)

    if args.save_overlay:
        img_bgr, _, _ = load_image_lossless(args.image)
        overlay_img = render_debug_overlay(img_bgr, doc)
        overlay_path = args.output_dir / doc.id / "overlay.png"
        cv2.imwrite(str(overlay_path), overlay_img)
        print(f"Overlay saved: {overlay_path}")

    print(
        f"Analyzed page {doc.id}: {len(doc.panels)} panels, "
        f"{len(doc.regions)} regions -> {args.output_dir / doc.id / 'document.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
