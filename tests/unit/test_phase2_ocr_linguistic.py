"""Unit and integration tests covering all Phase 2 OpenSpec scenarios (RF-06 to RF-09)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from mvte.application.use_cases.analyze_page import AnalyzePageUseCase
from mvte.application.use_cases.review_regions import ReviewRegionsUseCase
from mvte.application.use_cases.transcribe_page import TranscribePageUseCase
from mvte.domain.models.linguistic import TextOrientation
from mvte.domain.models.page import BoundingBox, PageDocument, ReadingDirection
from mvte.domain.ports.ocr import OcrLine
from mvte.infrastructure.storage.document_store import DocumentStore
from mvte.modules.linguistic_analysis.reconstructor import SentenceReconstructor
from mvte.modules.ocr.backends import OcrRegistry, estimate_text_orientation
from mvte.modules.page_analysis.analyzer import ContourPageAnalyzer
from mvte.modules.segmentation.segmenter import MaskSegmenter
from mvte.modules.text_association.associator import SpatialRegionAssociator
from mvte.modules.visual_detection.detector import MorphologicalBalloonDetector


def _make_text_page(path: Path) -> Path:
    img = np.full((600, 500, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (480, 580), (20, 20, 20), 4)
    cv2.rectangle(img, (24, 24), (476, 576), (60, 60, 60), -1)
    cv2.ellipse(img, (250, 200), (140, 80), 0, 0, 360, (255, 255, 255), -1)
    cv2.putText(img, "WAIT FOR", (165, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 2)
    cv2.putText(img, "ME!", (210, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 2)
    cv2.imwrite(str(path), img)
    return path


def test_rf06_orientation_estimation_and_replaceable_ocr_registry() -> None:
    horiz = np.full((60, 240, 3), 255, dtype=np.uint8)
    vert = np.full((240, 60, 3), 255, dtype=np.uint8)
    assert estimate_text_orientation(horiz) == TextOrientation.HORIZONTAL
    assert estimate_text_orientation(vert) == TextOrientation.VERTICAL

    class StubOcr:
        name = "stub_ocr"

        def recognize(self, crop_bgr: np.ndarray, orientation: TextOrientation = TextOrientation.UNKNOWN) -> list[OcrLine]:
            return [OcrLine("Hello!", BoundingBox(5, 5, 50, 25), 0.96, TextOrientation.HORIZONTAL, "en")]

        def unload(self) -> None:
            return None

    reg = OcrRegistry()
    reg.register("stub", StubOcr)
    assert reg.list_backends() == ["stub"]
    backend = reg.create("stub")
    assert backend.recognize(horiz)[0].text == "Hello!"


def test_rf07_rf08_hierarchy_and_multiline_sentence_grouping(tmp_path: Path) -> None:
    page_path = _make_text_page(tmp_path / "page.png")
    store = DocumentStore(tmp_path / "ws")

    doc = AnalyzePageUseCase(
        page_analyzer=ContourPageAnalyzer(),
        detector=MorphologicalBalloonDetector(),
        segmenter=MaskSegmenter(),
        associator=SpatialRegionAssociator(),
        store=store,
    ).execute(page_path, reading_direction=ReadingDirection.RTL, persist=True)

    class MultiLineStubOcr:
        name = "multiline_stub"

        def recognize(self, crop_bgr: np.ndarray, orientation: TextOrientation = TextOrientation.UNKNOWN) -> list[OcrLine]:
            return [
                OcrLine("WAIT FOR", BoundingBox(10, 10, 120, 35), 0.94, TextOrientation.HORIZONTAL, "en"),
                OcrLine("ME!", BoundingBox(20, 42, 80, 65), 0.92, TextOrientation.HORIZONTAL, "en"),
            ]

        def unload(self) -> None:
            return None

    doc = TranscribePageUseCase(
        ocr_backend=MultiLineStubOcr(),
        reconstructor=SentenceReconstructor(),
        store=store,
    ).execute(doc, persist=True)

    assert len(doc.text_blocks) >= 1
    tb = doc.text_blocks[0]
    assert tb.region_id == doc.regions[0].id
    assert len(tb.sentences) == 1
    assert tb.sentences[0].text == "WAIT FOR ME!"
    assert [t.text for t in tb.sentences[0].tokens] == ["WAIT", "FOR", "ME", "!"]

    # Roundtrip persistence preserves linguistic hierarchy
    loaded = PageDocument.from_json((tmp_path / "ws" / doc.id / "document.json").read_text(encoding="utf-8"))
    assert len(loaded.text_blocks) == len(doc.text_blocks)
    assert loaded.text_blocks[0].sentences[0].text == "WAIT FOR ME!"


def test_rf09_low_confidence_flag_and_manual_sentence_revision(tmp_path: Path) -> None:
    page_path = _make_text_page(tmp_path / "review_ocr.png")
    doc = AnalyzePageUseCase(
        page_analyzer=ContourPageAnalyzer(),
        detector=MorphologicalBalloonDetector(),
        segmenter=MaskSegmenter(),
        associator=SpatialRegionAssociator(),
    ).execute(page_path, persist=False)

    class NoisyOcr:
        name = "noisy"

        def recognize(self, crop_bgr: np.ndarray, orientation: TextOrientation = TextOrientation.UNKNOWN) -> list[OcrLine]:
            return [OcrLine("|||", BoundingBox(5, 5, 40, 20), 0.45, TextOrientation.HORIZONTAL, "en")]

        def unload(self) -> None:
            return None

    doc = TranscribePageUseCase(
        ocr_backend=NoisyOcr(),
        reconstructor=SentenceReconstructor(low_confidence_threshold=0.72),
    ).execute(doc, persist=False)

    sent = doc.text_blocks[0].sentences[0]
    assert sent.needs_review is True

    review = ReviewRegionsUseCase()
    review.update_sentence_text(doc, sent.id, "HEY!", note="Fixed OCR noise")
    assert sent.text == "HEY!"
    assert sent.needs_review is False
    assert sent.manual_override is True

    review.revert_last_revision(doc)
    assert sent.text == "|||"
