"""Phase 2 application use case: OCR transcription and linguistic reconstruction."""

from __future__ import annotations

import gc

from mvte.domain.models.linguistic import TextBlock, TextOrientation
from mvte.domain.models.page import PageDocument, VisualRegion
from mvte.domain.ports.ocr import LinguisticReconstructorPort, OcrBackendPort
from mvte.infrastructure.storage.document_store import DocumentStore, load_image_lossless


class TranscribePageUseCase:
    """Runs OCR on detected regions in panel reading order and builds linguistic hierarchy."""

    def __init__(
        self,
        ocr_backend: OcrBackendPort,
        reconstructor: LinguisticReconstructorPort,
        store: DocumentStore | None = None,
    ) -> None:
        self.ocr_backend = ocr_backend
        self.reconstructor = reconstructor
        self.store = store

    def execute(self, document: PageDocument, persist: bool = True) -> PageDocument:
        image_bgr, _, _ = load_image_lossless(document.source_path)
        panel_order = {p.id: p.reading_order for p in document.panels}

        ordered_regions = sorted(
            document.regions,
            key=lambda r: (
                panel_order.get(r.panel_id or "", 10**6),
                r.bbox.y1,
                -r.bbox.x1 if document.reading_direction.value == "rtl" else r.bbox.x1,
            ),
        )

        text_blocks: list[TextBlock] = []
        try:
            for order_idx, region in enumerate(ordered_regions):
                crop = self._crop_region(image_bgr, region)
                if crop.size == 0:
                    continue
                raw_lines = self.ocr_backend.recognize(crop, orientation=TextOrientation.UNKNOWN)
                # Offset line coordinates from crop-local to full-page coordinates.
                for line in raw_lines:
                    b = line.bbox
                    line.bbox = type(b)(
                        x1=region.bbox.x1 + b.x1,
                        y1=region.bbox.y1 + b.y1,
                        x2=region.bbox.x1 + b.x2,
                        y2=region.bbox.y1 + b.y2,
                    )
                tb = self.reconstructor.reconstruct(
                    region=region,
                    ocr_lines=raw_lines,
                    direction=document.reading_direction,
                    reading_order=order_idx,
                )
                text_blocks.append(tb)
        finally:
            self.ocr_backend.unload()
            gc.collect()

        document.text_blocks = text_blocks
        document.metadata["ocr_backend"] = self.ocr_backend.name

        if persist and self.store is not None:
            self.store.save(document)

        return document

    @staticmethod
    def _crop_region(image_bgr, region: VisualRegion):
        b = region.bbox
        return image_bgr[b.y1 : b.y2, b.x1 : b.x2]
