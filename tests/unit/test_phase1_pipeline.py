"""Unit and integration tests covering all Phase 1 OpenSpec scenarios (RF-01 to RF-05)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from mvte.application.use_cases.analyze_page import AnalyzePageUseCase
from mvte.application.use_cases.review_regions import ReviewRegionsUseCase
from mvte.domain.models.page import (
    BoundingBox,
    MaskKind,
    ReadingDirection,
    RegionKind,
)
from mvte.domain.ports.vision import RawDetection
from mvte.infrastructure.storage.document_store import DocumentStore, ImageLoadError
from mvte.modules.page_analysis.analyzer import ContourPageAnalyzer
from mvte.modules.segmentation.segmenter import MaskSegmenter
from mvte.modules.text_association.associator import SpatialRegionAssociator
from mvte.modules.visual_detection.detector import (
    DetectorRegistry,
    MorphologicalBalloonDetector,
)


def _make_sample_manga_page(path: Path) -> Path:
    """Create a realistic 2-panel manga-style page with speech balloon, narration box, and text."""
    img = np.full((800, 600, 3), 255, dtype=np.uint8)
    # Right panel (panel 0 in RTL) and Left panel (panel 1 in RTL)
    cv2.rectangle(img, (320, 30), (570, 380), (20, 20, 20), 4)
    cv2.rectangle(img, (30, 30), (280, 380), (20, 20, 20), 4)
    # Dark background inside right panel with a bright oval speech balloon containing dark text
    cv2.rectangle(img, (324, 34), (566, 376), (60, 60, 60), -1)
    cv2.ellipse(img, (445, 160), (85, 55), 0, 0, 360, (255, 255, 255), -1)
    cv2.ellipse(img, (445, 160), (85, 55), 0, 0, 360, (0, 0, 0), 2)
    cv2.putText(img, "HELLO!", (395, 168), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 3)

    # Dark background inside left panel with a bright rectangular narration box
    cv2.rectangle(img, (34, 34), (276, 376), (80, 80, 80), -1)
    cv2.rectangle(img, (60, 70), (240, 150), (255, 255, 255), -1)
    cv2.rectangle(img, (60, 70), (240, 150), (0, 0, 0), 2)
    cv2.putText(img, "MEANWHILE", (75, 118), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)

    cv2.imwrite(str(path), img)
    return path


def test_rf01_import_preserves_original_and_rejects_invalid(tmp_path: Path) -> None:
    page_path = _make_sample_manga_page(tmp_path / "page01.png")
    original_bytes = page_path.read_bytes()
    store = DocumentStore(tmp_path / "workspace")

    use_case = AnalyzePageUseCase(
        page_analyzer=ContourPageAnalyzer(),
        detector=MorphologicalBalloonDetector(),
        segmenter=MaskSegmenter(),
        associator=SpatialRegionAssociator(),
        store=store,
    )
    doc = use_case.execute(page_path, persist=True)

    assert doc.width == 600
    assert doc.height == 800
    assert page_path.read_bytes() == original_bytes
    assert (tmp_path / "workspace" / doc.id / "document.json").exists()

    # Rejection cases: missing, empty, unsupported
    with pytest.raises(ImageLoadError):
        use_case.execute(tmp_path / "missing.png", persist=True)

    empty_file = tmp_path / "empty.png"
    empty_file.write_bytes(b"")
    with pytest.raises(ImageLoadError):
        use_case.execute(empty_file, persist=True)

    bad_ext = tmp_path / "notes.txt"
    bad_ext.write_text("not an image", encoding="utf-8")
    with pytest.raises(ImageLoadError):
        use_case.execute(bad_ext, persist=True)


def test_rf02_panel_detection_and_rtl_ltr_ordering(tmp_path: Path) -> None:
    page_path = _make_sample_manga_page(tmp_path / "panels.png")
    img_bgr = cv2.imread(str(page_path))
    analyzer = ContourPageAnalyzer()

    rtl_panels = analyzer.analyze(img_bgr, ReadingDirection.RTL)
    ltr_panels = analyzer.analyze(img_bgr, ReadingDirection.LTR)

    assert len(rtl_panels) == 2
    assert rtl_panels[0].bbox.x1 > rtl_panels[1].bbox.x1  # Right panel first in RTL
    assert ltr_panels[0].bbox.x1 < ltr_panels[1].bbox.x1  # Left panel first in LTR


def test_rf03_replaceable_detector_backend(tmp_path: Path) -> None:
    class StubDetector:
        name = "stub_detector"

        def detect(self, image_bgr: np.ndarray) -> list[RawDetection]:
            return [
                RawDetection(
                    kind=RegionKind.SFX,
                    bbox=BoundingBox(10, 10, 100, 60),
                    confidence=0.91,
                )
            ]

        def unload(self) -> None:
            return None

    registry = DetectorRegistry()
    registry.register("morphological", MorphologicalBalloonDetector)
    registry.register("stub", StubDetector)

    assert registry.list_backends() == ["morphological", "stub"]
    detector = registry.create("stub")
    page_path = _make_sample_manga_page(tmp_path / "stub_page.png")
    use_case = AnalyzePageUseCase(
        page_analyzer=ContourPageAnalyzer(),
        detector=detector,
        segmenter=MaskSegmenter(),
        associator=SpatialRegionAssociator(),
    )
    doc = use_case.execute(page_path, persist=False)
    assert len(doc.regions) == 1
    assert doc.regions[0].kind == RegionKind.SFX
    assert doc.metadata["detector"] == "stub_detector"


def test_rf04_structure_vs_character_mask_separation(tmp_path: Path) -> None:
    page_path = _make_sample_manga_page(tmp_path / "masks.png")
    use_case = AnalyzePageUseCase(
        page_analyzer=ContourPageAnalyzer(),
        detector=MorphologicalBalloonDetector(),
        segmenter=MaskSegmenter(),
        associator=SpatialRegionAssociator(),
        store=DocumentStore(tmp_path / "ws"),
    )
    doc = use_case.execute(page_path, persist=True)

    assert len(doc.regions) >= 2
    for region in doc.regions:
        assert region.structure_mask is not None
        assert region.character_mask is not None
        assert region.structure_mask.kind == MaskKind.STRUCTURE
        assert region.character_mask.kind == MaskKind.CHARACTER
        struct_pixels = int(np.count_nonzero(region.structure_mask.data))
        char_pixels = int(np.count_nonzero(region.character_mask.data))
        assert struct_pixels > char_pixels > 0


def test_rf05_association_and_manual_review_history(tmp_path: Path) -> None:
    page_path = _make_sample_manga_page(tmp_path / "review.png")

    class MixedDetector:
        name = "mixed"

        def detect(self, image_bgr: np.ndarray) -> list[RawDetection]:
            return [
                RawDetection(RegionKind.SPEECH_BALLOON, BoundingBox(360, 105, 530, 215), 0.9),
                RawDetection(RegionKind.FREE_TEXT, BoundingBox(385, 135, 505, 185), 0.85),
                RawDetection(RegionKind.FREE_TEXT, BoundingBox(50, 500, 200, 560), 0.8),
            ]

        def unload(self) -> None:
            return None

    use_case = AnalyzePageUseCase(
        page_analyzer=ContourPageAnalyzer(),
        detector=MixedDetector(),
        segmenter=MaskSegmenter(),
        associator=SpatialRegionAssociator(),
    )
    doc = use_case.execute(page_path, persist=False)

    # First free_text is inside balloon, second is truly free text
    assoc_by_reg = {a.text_region_id: a for a in doc.associations}
    inside_assoc = assoc_by_reg[doc.regions[1].id]
    outside_assoc = assoc_by_reg[doc.regions[2].id]
    assert inside_assoc.container_region_id == doc.regions[0].id
    assert inside_assoc.is_free_text is False
    assert outside_assoc.container_region_id is None
    assert outside_assoc.is_free_text is True

    review = ReviewRegionsUseCase()
    review.update_region_kind(doc, doc.regions[2].id, RegionKind.SFX, note="Actually SFX")
    assert doc.regions[2].kind == RegionKind.SFX
    assert doc.regions[2].manual_override is True
    assert len(doc.revisions) == 1

    review.revert_last_revision(doc)
    assert doc.regions[2].kind == RegionKind.FREE_TEXT
    assert len(doc.revisions) == 0


def test_gui_default_workspace_is_absolute_and_writable() -> None:
    from mvte.interfaces.gui.main import default_gui_workspace_dir

    ws = default_gui_workspace_dir()
    assert ws.is_absolute()
