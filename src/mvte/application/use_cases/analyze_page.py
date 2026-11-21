"""Phase 1 application use case: global page analysis, detection, segmentation, and association."""

from __future__ import annotations

import gc
from pathlib import Path

from mvte.domain.models.page import PageDocument, ReadingDirection
from mvte.domain.ports.vision import (
    PageAnalyzerPort,
    RegionAssociatorPort,
    SegmenterPort,
    VisualDetectorPort,
)
from mvte.infrastructure.storage.document_store import DocumentStore, load_image_lossless


class ModelLifecycleManager:
    """Ensures vision/ML backends are explicitly unloaded after each stage."""

    @staticmethod
    def release(detector: VisualDetectorPort) -> None:
        detector.unload()
        gc.collect()


class AnalyzePageUseCase:
    """Orchestrates Phase 1 page reading without mutating the original image."""

    def __init__(
        self,
        page_analyzer: PageAnalyzerPort,
        detector: VisualDetectorPort,
        segmenter: SegmenterPort,
        associator: RegionAssociatorPort,
        store: DocumentStore | None = None,
    ) -> None:
        self.page_analyzer = page_analyzer
        self.detector = detector
        self.segmenter = segmenter
        self.associator = associator
        self.store = store

    def execute(
        self,
        image_path: Path | str,
        reading_direction: ReadingDirection = ReadingDirection.RTL,
        persist: bool = True,
    ) -> PageDocument:
        image_bgr, width, height = load_image_lossless(image_path)
        document = PageDocument.create(
            source_path=str(Path(image_path).resolve()),
            width=width,
            height=height,
            reading_direction=reading_direction,
            metadata={"detector": self.detector.name},
        )

        panels = self.page_analyzer.analyze(image_bgr, reading_direction)
        try:
            detections = self.detector.detect(image_bgr)
        finally:
            ModelLifecycleManager.release(self.detector)

        regions = self.segmenter.segment(image_bgr, detections)
        associations = self.associator.associate(panels, regions)

        document.panels = panels
        document.regions = regions
        document.associations = associations

        if persist and self.store is not None:
            self.store.save(document)

        return document
