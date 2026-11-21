"""MAM-independent service/process integration contract for MVTE."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mvte.application.use_cases.analyze_page import AnalyzePageUseCase
from mvte.application.use_cases.batch_pipeline import BatchRunner, FullPagePipeline
from mvte.application.use_cases.reconstruct_page import ReconstructPageUseCase
from mvte.application.use_cases.transcribe_page import TranscribePageUseCase
from mvte.application.use_cases.translate_page import TranslatePageUseCase
from mvte.domain.models.page import ReadingDirection
from mvte.domain.ports.ocr import OcrBackendPort
from mvte.domain.ports.translation import TranslatorBackendPort
from mvte.domain.ports.vision import VisualDetectorPort
from mvte.infrastructure.persistence.context_store import SqliteContextStore
from mvte.infrastructure.storage.document_store import DocumentStore
from mvte.modules.context_management.manager import ContextManager
from mvte.modules.linguistic_analysis.reconstructor import SentenceReconstructor
from mvte.modules.ocr.backends import RapidOcrAdapter
from mvte.modules.page_analysis.analyzer import ContourPageAnalyzer
from mvte.modules.rendering.compositor import LayeredPageCompositor
from mvte.modules.segmentation.segmenter import MaskSegmenter
from mvte.modules.text_association.associator import SpatialRegionAssociator
from mvte.modules.text_cleaning.cleaner import SelectiveTextCleaner
from mvte.modules.translation.engine import HybridTranslationEngine
from mvte.modules.typography.engine import LocalFontCatalog, TypographyEngine
from mvte.modules.visual_detection.detector import MorphologicalBalloonDetector


@dataclass
class TranslationJobRequest:
    """Stable input DTO for external callers (CLI, IPC, or future MAM adapter)."""

    image_paths: list[str]
    work_id: str
    chapter_id: str
    source_lang: str
    target_lang: str
    workspace_dir: str = "storage/runs"
    context_db_path: str = "storage/context.sqlite"
    models_dir: str | None = None
    reading_direction: str = "rtl"


@dataclass
class TranslationJobResponse:
    """Stable output DTO decoupled from MVTE internal domain classes."""

    total: int
    succeeded: int
    failed: int
    models_dir_used: str
    items: list[dict[str, Any]] = field(default_factory=list)


def resolve_models_dir(explicit: str | None = None) -> Path:
    """Allow sharing local model weights via MVTE_MODELS_DIR without code coupling."""
    raw = explicit or os.environ.get("MVTE_MODELS_DIR") or "models"
    return Path(raw)


def execute_job(
    request: TranslationJobRequest,
    *,
    detector: VisualDetectorPort | None = None,
    ocr_backend: OcrBackendPort | None = None,
    translator_backend: TranslatorBackendPort | None = None,
) -> TranslationJobResponse:
    """Execute a complete batch translation job as an isolated service call."""
    models_dir = resolve_models_dir(request.models_dir)
    doc_store = DocumentStore(request.workspace_dir)
    ctx_store = SqliteContextStore(request.context_db_path)

    if translator_backend is None:
        raise ValueError("A local TranslatorBackendPort instance must be configured for execute_job.")

    pipeline = FullPagePipeline(
        analyze_uc=AnalyzePageUseCase(
            page_analyzer=ContourPageAnalyzer(),
            detector=detector or MorphologicalBalloonDetector(),
            segmenter=MaskSegmenter(),
            associator=SpatialRegionAssociator(),
            store=doc_store,
        ),
        transcribe_uc=TranscribePageUseCase(
            ocr_backend=ocr_backend or RapidOcrAdapter(),
            reconstructor=SentenceReconstructor(),
            store=doc_store,
        ),
        translate_uc=TranslatePageUseCase(
            context_store=ctx_store,
            context_manager=ContextManager(ctx_store),
            engine=HybridTranslationEngine(primary_backend=translator_backend),
            document_store=doc_store,
        ),
        reconstruct_uc=ReconstructPageUseCase(
            cleaner=SelectiveTextCleaner(),
            typography=TypographyEngine(LocalFontCatalog()),
            compositor=LayeredPageCompositor(),
            store=doc_store,
        ),
    )

    summary = BatchRunner(pipeline).run_batch(
        image_paths=request.image_paths,
        work_id=request.work_id,
        chapter_id=request.chapter_id,
        source_lang=request.source_lang,
        target_lang=request.target_lang,
        reading_direction=ReadingDirection(request.reading_direction),
        persist=True,
    )

    return TranslationJobResponse(
        total=summary.total,
        succeeded=summary.succeeded,
        failed=summary.failed,
        models_dir_used=str(models_dir),
        items=[
            {
                "source_path": item.source_path,
                "success": item.success,
                "document_id": item.document_id,
                "translated_path": item.translated_path,
                "validation_passed": item.validation_passed,
                "elapsed_ms": item.elapsed_ms,
                "error": item.error,
            }
            for item in summary.items
        ],
    )
