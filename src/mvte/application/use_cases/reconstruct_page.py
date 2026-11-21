"""Phase 4 application use case: text cleaning, typography planning, and composition."""

from __future__ import annotations

from pathlib import Path

import cv2

from mvte.domain.models.page import PageDocument
from mvte.domain.models.rendering import ReconstructionResult, TypographyPlan
from mvte.domain.ports.rendering import (
    PageCompositorPort,
    TextCleanerPort,
    TypographyEnginePort,
)
from mvte.infrastructure.storage.document_store import DocumentStore, load_image_lossless


class ReconstructPageUseCase:
    """Produces cleaned and translated page outputs without mutating the original image."""

    def __init__(
        self,
        cleaner: TextCleanerPort,
        typography: TypographyEnginePort,
        compositor: PageCompositorPort,
        store: DocumentStore,
    ) -> None:
        self.cleaner = cleaner
        self.typography = typography
        self.compositor = compositor
        self.store = store

    def execute(self, document: PageDocument, persist: bool = True) -> ReconstructionResult:
        original_bgr, _, _ = load_image_lossless(document.source_path)
        cleaned_res = self.cleaner.clean(original_bgr, document)

        translations_by_region = self._collect_region_translations(document)
        plans: list[TypographyPlan] = []
        for region in document.regions:
            translated = translations_by_region.get(region.id, "").strip()
            if not translated:
                continue
            plans.append(self.typography.plan_region(cleaned_res.cleaned_bgr, region, translated))

        translated_bgr = self.compositor.compose(cleaned_res.cleaned_bgr, plans)

        cleaned_path: str | None = None
        translated_path: str | None = None
        if persist:
            out_dir = self.store.workspace_dir / document.id / "outputs"
            out_dir.mkdir(parents=True, exist_ok=True)
            c_file = out_dir / "cleaned.png"
            t_file = out_dir / "translated.png"
            cv2.imwrite(str(c_file), cleaned_res.cleaned_bgr)
            cv2.imwrite(str(t_file), translated_bgr)
            cleaned_path = str(c_file)
            translated_path = str(t_file)

            document.metadata["outputs"] = {
                "cleaned_path": cleaned_path,
                "translated_path": translated_path,
                "typography_plans": [p.to_dict() for p in plans],
            }
            self.store.save(document)

        return ReconstructionResult(
            cleaned_path=cleaned_path,
            translated_path=translated_path,
            plans=plans,
            cleaning_reports=cleaned_res.reports,
        )

    @staticmethod
    def _collect_region_translations(document: PageDocument) -> dict[str, str]:
        by_region: dict[str, list[str]] = {}
        for tb in document.text_blocks:
            texts = [s.translation.strip() for s in tb.sentences if s.translation.strip()]
            if texts:
                by_region.setdefault(tb.region_id, []).extend(texts)
        return {rid: " ".join(parts) for rid, parts in by_region.items()}
