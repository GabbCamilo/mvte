"""Phase 3 application use case: multi-scale contextual translation and TM persistence."""

from __future__ import annotations

from mvte.domain.models.page import PageDocument
from mvte.domain.models.translation import TranslationMemoryEntry
from mvte.domain.ports.translation import ContextStorePort
from mvte.infrastructure.storage.document_store import DocumentStore
from mvte.modules.context_management.manager import ContextManager
from mvte.modules.translation.engine import HybridTranslationEngine


class TranslatePageUseCase:
    """Translates all sentences in a PageDocument using 3-scale context and local backends."""

    def __init__(
        self,
        context_store: ContextStorePort,
        context_manager: ContextManager,
        engine: HybridTranslationEngine,
        document_store: DocumentStore | None = None,
    ) -> None:
        self.context_store = context_store
        self.context_manager = context_manager
        self.engine = engine
        self.document_store = document_store

    def execute(
        self,
        document: PageDocument,
        work_id: str,
        chapter_id: str,
        source_lang: str,
        target_lang: str,
        persist: bool = True,
    ) -> PageDocument:
        ordered_blocks = sorted(document.text_blocks, key=lambda tb: tb.reading_order)

        try:
            for block in ordered_blocks:
                for sentence in sorted(block.sentences, key=lambda s: s.reading_order):
                    if not sentence.text.strip():
                        continue
                    packet = self.context_manager.build_packet(
                        document=document,
                        sentence=sentence,
                        work_id=work_id,
                        chapter_id=chapter_id,
                        source_lang=source_lang,
                        target_lang=target_lang,
                    )
                    result = self.engine.translate(packet)
                    sentence.translation = result.translated_text
                    sentence.translation_confidence = result.confidence
                    sentence.translation_needs_review = result.needs_review

                    if result.translated_text and not result.used_tm and not result.needs_review:
                        self.context_store.add_tm_entry(
                            TranslationMemoryEntry.create(
                                work_id=work_id,
                                source_lang=source_lang,
                                target_lang=target_lang,
                                source_text=sentence.text,
                                target_text=result.translated_text,
                                context_summary=f"chapter:{chapter_id}",
                            )
                        )
        finally:
            self.engine.unload()

        document.metadata["target_lang"] = target_lang
        document.metadata["work_id"] = work_id
        if persist and self.document_store is not None:
            self.document_store.save(document)

        return document
