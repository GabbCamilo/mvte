"""Full E2E page pipeline and fault-isolated batch runner (Phase 5)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from mvte.application.use_cases.analyze_page import AnalyzePageUseCase
from mvte.application.use_cases.reconstruct_page import ReconstructPageUseCase
from mvte.application.use_cases.transcribe_page import TranscribePageUseCase
from mvte.application.use_cases.translate_page import TranslatePageUseCase
from mvte.domain.models.page import PageDocument, ReadingDirection
from mvte.domain.models.rendering import ReconstructionResult
from mvte.modules.validation.validator import PageValidationEngine, ValidationReport


@dataclass
class FullPageResult:
    document: PageDocument
    reconstruction: ReconstructionResult
    validation: ValidationReport
    elapsed_ms: float


@dataclass
class BatchItemResult:
    source_path: str
    success: bool
    document_id: str | None = None
    translated_path: str | None = None
    validation_passed: bool = False
    elapsed_ms: float = 0.0
    error: str | None = None


@dataclass
class BatchSummary:
    total: int
    succeeded: int
    failed: int
    items: list[BatchItemResult] = field(default_factory=list)


class FullPagePipeline:
    """Executes Phases 1 -> 2 -> 3 -> 4 -> 5 on a single page."""

    def __init__(
        self,
        analyze_uc: AnalyzePageUseCase,
        transcribe_uc: TranscribePageUseCase,
        translate_uc: TranslatePageUseCase,
        reconstruct_uc: ReconstructPageUseCase,
        validator: PageValidationEngine | None = None,
    ) -> None:
        self.analyze_uc = analyze_uc
        self.transcribe_uc = transcribe_uc
        self.translate_uc = translate_uc
        self.reconstruct_uc = reconstruct_uc
        self.validator = validator or PageValidationEngine()

    def run(
        self,
        image_path: Path | str,
        work_id: str,
        chapter_id: str,
        source_lang: str,
        target_lang: str,
        reading_direction: ReadingDirection = ReadingDirection.RTL,
        persist: bool = True,
    ) -> FullPageResult:
        t0 = time.perf_counter()
        doc = self.analyze_uc.execute(image_path, reading_direction=reading_direction, persist=persist)
        doc = self.transcribe_uc.execute(doc, persist=persist)
        doc = self.translate_uc.execute(
            doc, work_id=work_id, chapter_id=chapter_id, source_lang=source_lang, target_lang=target_lang, persist=persist
        )
        recon = self.reconstruct_uc.execute(doc, persist=persist)
        report = self.validator.validate(doc, recon)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        return FullPageResult(
            document=doc,
            reconstruction=recon,
            validation=report,
            elapsed_ms=round(elapsed_ms, 2),
        )


class BatchRunner:
    """Runs FullPagePipeline across multiple pages with per-page fault isolation."""

    def __init__(self, pipeline: FullPagePipeline) -> None:
        self.pipeline = pipeline

    def run_batch(
        self,
        image_paths: list[Path | str],
        work_id: str,
        chapter_id: str,
        source_lang: str,
        target_lang: str,
        reading_direction: ReadingDirection = ReadingDirection.RTL,
        persist: bool = True,
    ) -> BatchSummary:
        items: list[BatchItemResult] = []
        succeeded = 0
        failed = 0

        for img_path in image_paths:
            t0 = time.perf_counter()
            try:
                res = self.pipeline.run(
                    image_path=img_path,
                    work_id=work_id,
                    chapter_id=chapter_id,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    reading_direction=reading_direction,
                    persist=persist,
                )
                succeeded += 1
                items.append(
                    BatchItemResult(
                        source_path=str(img_path),
                        success=True,
                        document_id=res.document.id,
                        translated_path=res.reconstruction.translated_path,
                        validation_passed=res.validation.passed,
                        elapsed_ms=res.elapsed_ms,
                    )
                )
            except Exception as exc:
                failed += 1
                items.append(
                    BatchItemResult(
                        source_path=str(img_path),
                        success=False,
                        elapsed_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )

        return BatchSummary(total=len(image_paths), succeeded=succeeded, failed=failed, items=items)
