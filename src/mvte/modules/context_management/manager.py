"""Three-scale context management (Micro, Meso, Macro) with selective retrieval."""

from __future__ import annotations

from mvte.domain.models.linguistic import Sentence
from mvte.domain.models.page import PageDocument
from mvte.domain.models.translation import (
    GlossaryTerm,
    TranslationContextPacket,
    TranslationMemoryEntry,
)
from mvte.domain.ports.translation import ContextStorePort


class ContextManager:
    """Builds selective TranslationContextPacket for each sentence on a page."""

    def __init__(self, store: ContextStorePort, meso_window: int = 2, max_tm_matches: int = 3) -> None:
        self.store = store
        self.meso_window = meso_window
        self.max_tm_matches = max_tm_matches

    def build_packet(
        self,
        document: PageDocument,
        sentence: Sentence,
        work_id: str,
        chapter_id: str,
        source_lang: str,
        target_lang: str,
    ) -> TranslationContextPacket:
        # Micro: current sentence and its tokens
        micro_tokens = [t.text for t in sentence.tokens]

        # Meso: surrounding sentences in reading order on the same page
        ordered_sentences = [
            s.text for tb in document.text_blocks for s in tb.sentences if s.text.strip()
        ]
        meso = self._extract_meso_window(ordered_sentences, sentence.text)

        # Macro: selective glossary & TM matching only relevant entries
        all_glossary = self.store.list_glossary_terms(work_id)
        glossary_matches = self._select_relevant_glossary(sentence.text, all_glossary)

        all_tm = self.store.list_tm_entries(work_id, source_lang, target_lang)
        tm_matches = self._select_relevant_tm(sentence.text, all_tm)

        notes = self.store.list_narrative_notes(work_id)[-3:]

        return TranslationContextPacket(
            work_id=work_id,
            chapter_id=chapter_id,
            source_lang=source_lang,
            target_lang=target_lang,
            micro_sentence=sentence.text,
            micro_tokens=micro_tokens,
            meso_surrounding_sentences=meso,
            macro_glossary_matches=glossary_matches,
            macro_tm_matches=tm_matches,
            macro_narrative_notes=notes,
        )

    def _extract_meso_window(self, ordered_sentences: list[str], target_text: str) -> list[str]:
        if target_text not in ordered_sentences:
            return ordered_sentences[: self.meso_window * 2]
        idx = ordered_sentences.index(target_text)
        start = max(0, idx - self.meso_window)
        end = min(len(ordered_sentences), idx + self.meso_window + 1)
        return [s for i, s in enumerate(ordered_sentences[start:end], start=start) if i != idx]

    @staticmethod
    def _select_relevant_glossary(text: str, terms: list[GlossaryTerm]) -> list[GlossaryTerm]:
        lowered = text.lower()
        return [t for t in terms if t.source_term.lower() in lowered]

    def _select_relevant_tm(
        self, text: str, entries: list[TranslationMemoryEntry]
    ) -> list[TranslationMemoryEntry]:
        text_words = set(text.lower().split())
        scored: list[tuple[float, TranslationMemoryEntry]] = []
        for entry in entries:
            if entry.source_text.strip().lower() == text.strip().lower():
                scored.append((1.0, entry))
                continue
            entry_words = set(entry.source_text.lower().split())
            if not text_words or not entry_words:
                continue
            jaccard = len(text_words & entry_words) / len(text_words | entry_words)
            if jaccard >= 0.35:
                scored.append((jaccard, entry))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [pair[1] for pair in scored[: self.max_tm_matches]]
