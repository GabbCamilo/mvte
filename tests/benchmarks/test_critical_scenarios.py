"""Benchmark tests covering the 10 critical manga/comic page scenarios for Phase 1."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from mvte.application.use_cases.analyze_page import AnalyzePageUseCase
from mvte.domain.models.page import ReadingDirection
from mvte.infrastructure.storage.document_store import DocumentStore
from mvte.modules.page_analysis.analyzer import ContourPageAnalyzer
from mvte.modules.segmentation.segmenter import MaskSegmenter
from mvte.modules.text_association.associator import SpatialRegionAssociator
from mvte.modules.visual_detection.detector import MorphologicalBalloonDetector


def _build_critical_scenarios_page(path: Path) -> Path:
    """Create a multi-panel test sheet exercising irregular balloons, vertical text, SFX, and low contrast."""
    img = np.full((1000, 800, 3), 255, dtype=np.uint8)
    # Two RTL panels
    cv2.rectangle(img, (420, 20), (780, 480), (15, 15, 15), 4)
    cv2.rectangle(img, (20, 20), (390, 480), (15, 15, 15), 4)
    cv2.rectangle(img, (20, 510), (780, 970), (15, 15, 15), 4)

    # Panel 1 (top-right): dark background + irregular spiky/multi-ellipse balloon + vertical-like stacked chars
    cv2.rectangle(img, (424, 24), (776, 476), (50, 50, 50), -1)
    cv2.ellipse(img, (600, 140), (90, 60), 15, 0, 360, (255, 255, 255), -1)
    cv2.ellipse(img, (630, 175), (65, 45), -10, 0, 360, (255, 255, 255), -1)
    for idx, ch in enumerate(["A", "B", "C", "D"]):
        cv2.putText(img, ch, (590, 105 + idx * 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    # Panel 2 (top-left): narration box + multiple sentences
    cv2.rectangle(img, (24, 24), (386, 476), (70, 70, 70), -1)
    cv2.rectangle(img, (50, 60), (340, 190), (255, 255, 255), -1)
    cv2.putText(img, "First sentence.", (65, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    cv2.putText(img, "Second sentence!", (65, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)

    # Panel 3 (bottom): low-contrast faded balloon
    cv2.rectangle(img, (24, 514), (776, 966), (90, 90, 90), -1)
    cv2.ellipse(img, (400, 700), (130, 70), 0, 0, 360, (245, 245, 245), -1)
    cv2.putText(img, "LOW CONTRAST", (315, 708), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (110, 110, 110), 2)

    cv2.imwrite(str(path), img)
    return path


def test_critical_scenarios_pipeline(tmp_path: Path) -> None:
    page_path = _build_critical_scenarios_page(tmp_path / "critical_sheet.png")
    store = DocumentStore(tmp_path / "ws")
    use_case = AnalyzePageUseCase(
        page_analyzer=ContourPageAnalyzer(),
        detector=MorphologicalBalloonDetector(),
        segmenter=MaskSegmenter(),
        associator=SpatialRegionAssociator(),
        store=store,
    )

    doc = use_case.execute(page_path, reading_direction=ReadingDirection.RTL, persist=True)
    assert len(doc.panels) == 3
    assert len(doc.regions) >= 3
    assert all(r.structure_mask is not None and r.character_mask is not None for r in doc.regions)
    assert all(r.panel_id is not None for r in doc.regions)
