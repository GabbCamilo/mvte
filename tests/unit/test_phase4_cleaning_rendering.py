"""Unit and integration tests covering Phase 4 OpenSpec scenarios (RF-14 to RF-17)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from mvte.application.use_cases.analyze_page import AnalyzePageUseCase
from mvte.application.use_cases.reconstruct_page import ReconstructPageUseCase
from mvte.domain.models.linguistic import Sentence, TextBlock
from mvte.infrastructure.storage.document_store import DocumentStore
from mvte.modules.page_analysis.analyzer import ContourPageAnalyzer
from mvte.modules.rendering.compositor import LayeredPageCompositor
from mvte.modules.segmentation.segmenter import MaskSegmenter
from mvte.modules.text_association.associator import SpatialRegionAssociator
from mvte.modules.text_cleaning.cleaner import SelectiveTextCleaner
from mvte.modules.typography.engine import LocalFontCatalog, TypographyEngine
from mvte.modules.visual_detection.detector import MorphologicalBalloonDetector


def _make_cleanable_page(path: Path) -> Path:
    img = np.full((600, 500, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (480, 580), (20, 20, 20), 4)
    cv2.rectangle(img, (24, 24), (476, 576), (55, 55, 55), -1)

    # Region 1: Uniform white speech balloon
    cv2.ellipse(img, (250, 150), (140, 65), 0, 0, 360, (255, 255, 255), -1)
    cv2.putText(img, "ORIGINAL", (175, 158), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 2)

    # Region 2: Textured/gradient narration box requiring inpainting (light texture > 225, dark text)
    cv2.rectangle(img, (80, 320), (420, 440), (245, 245, 245), -1)
    for x in range(84, 420, 10):
        cv2.line(img, (x, 322), (x, 438), (228, 228, 228), 1)
    cv2.putText(img, "TEXTURED", (165, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 2)

    cv2.imwrite(str(path), img)
    return path


def test_rf14_to_rf17_cleaning_typography_and_composition(tmp_path: Path) -> None:
    page_path = _make_cleanable_page(tmp_path / "page.png")
    orig_bytes = page_path.read_bytes()
    store = DocumentStore(tmp_path / "ws")

    doc = AnalyzePageUseCase(
        page_analyzer=ContourPageAnalyzer(),
        detector=MorphologicalBalloonDetector(),
        segmenter=MaskSegmenter(),
        associator=SpatialRegionAssociator(),
        store=store,
    ).execute(page_path, persist=True)

    assert len(doc.regions) >= 2
    for idx, region in enumerate(doc.regions):
        sent = Sentence(
            id=f"s{idx}",
            text="ORIGINAL",
            translation="Texto traduzido com clareza",
        )
        doc.text_blocks.append(
            TextBlock.create(region_id=region.id, panel_id=region.panel_id, sentences=[sent])
        )

    uc = ReconstructPageUseCase(
        cleaner=SelectiveTextCleaner(),
        typography=TypographyEngine(LocalFontCatalog()),
        compositor=LayeredPageCompositor(),
        store=store,
    )
    res = uc.execute(doc, persist=True)

    assert page_path.read_bytes() == orig_bytes
    assert res.cleaned_path is not None and Path(res.cleaned_path).exists()
    assert res.translated_path is not None and Path(res.translated_path).exists()

    out_img = cv2.imread(res.translated_path)
    assert out_img.shape[:2] == (600, 500)
    assert len(res.plans) == len(doc.regions)
    assert all(plan.font_match.is_exact_match is False for plan in res.plans)


def test_rf16_never_truncates_and_flags_overflow(tmp_path: Path) -> None:
    page_path = _make_cleanable_page(tmp_path / "overflow.png")
    doc = AnalyzePageUseCase(
        page_analyzer=ContourPageAnalyzer(),
        detector=MorphologicalBalloonDetector(),
        segmenter=MaskSegmenter(),
        associator=SpatialRegionAssociator(),
    ).execute(page_path, persist=False)

    very_long = " ".join(["palavra"] * 45)
    img_bgr = cv2.imread(str(page_path))
    plan = TypographyEngine(LocalFontCatalog(), init_font_size=22, min_font_size=10).plan_region(
        img_bgr, doc.regions[0], very_long
    )

    # All words preserved (no truncation) and manual review flagged
    assert plan.wrapped_text.split() == very_long.split()
    assert plan.needs_manual_review is True
    assert plan.overflow_reason == "text_exceeds_min_legible_box"
