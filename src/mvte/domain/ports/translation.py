"""Domain port contracts for Phase 3 context management and hybrid translation."""

from __future__ import annotations

from typing import Protocol

from mvte.domain.models.translation import (
    GlossaryTerm,
    TranslationContextPacket,
    TranslationMemoryEntry,
    TranslationResult,
)


class ContextStorePort(Protocol):
    """Local persistence for glossary, translation memory, and narrative notes."""

    def add_glossary_term(self, term: GlossaryTerm) -> None:
        ...

    def list_glossary_terms(self, work_id: str) -> list[GlossaryTerm]:
        ...

    def add_tm_entry(self, entry: TranslationMemoryEntry) -> None:
        ...

    def list_tm_entries(
        self, work_id: str, source_lang: str, target_lang: str
    ) -> list[TranslationMemoryEntry]:
        ...

    def add_narrative_note(self, work_id: str, note: str) -> None:
        ...

    def list_narrative_notes(self, work_id: str) -> list[str]:
        ...


class TranslatorBackendPort(Protocol):
    """Replaceable local translation backend (NMT or local LLM)."""

    name: str

    def translate(self, text: str, packet: TranslationContextPacket) -> TranslationResult:
        ...

    def unload(self) -> None:
        ...
