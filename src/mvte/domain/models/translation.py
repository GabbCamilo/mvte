"""Translation, glossary, translation memory, and multi-scale context domain models (Phase 3)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class GlossaryTerm:
    """Terminology entry scoped to a manga/comic work."""

    id: str
    work_id: str
    source_term: str
    target_term: str
    category: str = "term"
    notes: str = ""

    @classmethod
    def create(
        cls,
        work_id: str,
        source_term: str,
        target_term: str,
        category: str = "term",
        notes: str = "",
    ) -> GlossaryTerm:
        return cls(
            id=str(uuid.uuid4()),
            work_id=work_id,
            source_term=source_term,
            target_term=target_term,
            category=category,
            notes=notes,
        )


@dataclass
class TranslationMemoryEntry:
    """Persisted source-target translation pair for reuse and consistency."""

    id: str
    work_id: str
    source_lang: str
    target_lang: str
    source_text: str
    target_text: str
    context_summary: str = ""

    @classmethod
    def create(
        cls,
        work_id: str,
        source_lang: str,
        target_lang: str,
        source_text: str,
        target_text: str,
        context_summary: str = "",
    ) -> TranslationMemoryEntry:
        return cls(
            id=str(uuid.uuid4()),
            work_id=work_id,
            source_lang=source_lang,
            target_lang=target_lang,
            source_text=source_text,
            target_text=target_text,
            context_summary=context_summary,
        )


@dataclass
class TranslationContextPacket:
    """Three-scale context (Micro, Meso, Macro) selectively retrieved for a sentence."""

    work_id: str
    chapter_id: str
    source_lang: str
    target_lang: str
    micro_sentence: str
    micro_tokens: list[str] = field(default_factory=list)
    meso_surrounding_sentences: list[str] = field(default_factory=list)
    macro_glossary_matches: list[GlossaryTerm] = field(default_factory=list)
    macro_tm_matches: list[TranslationMemoryEntry] = field(default_factory=list)
    macro_narrative_notes: list[str] = field(default_factory=list)


@dataclass
class TranslationResult:
    """Output of a translation backend or hybrid engine."""

    translated_text: str
    confidence: float
    needs_review: bool = False
    review_reason: str = ""
    used_tm: bool = False
