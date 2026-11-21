"""Unit and integration tests covering all Phase 3 OpenSpec scenarios (RF-10 to RF-13)."""

from __future__ import annotations

from pathlib import Path

from mvte.application.use_cases.review_regions import ReviewRegionsUseCase
from mvte.application.use_cases.translate_page import TranslatePageUseCase
from mvte.domain.models.linguistic import Sentence, TextBlock
from mvte.domain.models.page import PageDocument
from mvte.domain.models.translation import (
    GlossaryTerm,
    TranslationContextPacket,
    TranslationMemoryEntry,
    TranslationResult,
)
from mvte.infrastructure.persistence.context_store import SqliteContextStore
from mvte.infrastructure.storage.document_store import DocumentStore
from mvte.modules.context_management.manager import ContextManager
from mvte.modules.translation.engine import HybridTranslationEngine, TranslationRegistry


def _make_transcribed_doc(tmp_path: Path) -> PageDocument:
    doc = PageDocument.create(source_path=str(tmp_path / "p1.png"), width=600, height=800)
    s1 = Sentence(id="s1", text="Where is Akira?", reading_order=0, language="en")
    s2 = Sentence(id="s2", text="He went to the Guild.", reading_order=1, language="en")
    tb = TextBlock.create(region_id="r1", panel_id="p1", reading_order=0, sentences=[s1, s2])
    doc.text_blocks.append(tb)
    return doc


def test_rf10_selective_three_scale_context_packet(tmp_path: Path) -> None:
    store = SqliteContextStore(tmp_path / "ctx.sqlite")
    store.add_glossary_term(GlossaryTerm.create("work1", "Akira", "Akira"))
    store.add_glossary_term(GlossaryTerm.create("work1", "UnrelatedTerm", "TermoIrrelevante"))
    store.add_narrative_note("work1", "Akira left the village in chapter 1.")

    doc = _make_transcribed_doc(tmp_path)
    manager = ContextManager(store, meso_window=1)
    packet = manager.build_packet(doc, doc.text_blocks[0].sentences[0], "work1", "ch2", "en", "pt-BR")

    assert packet.micro_sentence == "Where is Akira?"
    assert packet.meso_surrounding_sentences == ["He went to the Guild."]
    assert [g.source_term for g in packet.macro_glossary_matches] == ["Akira"]
    assert packet.macro_narrative_notes == ["Akira left the village in chapter 1."]


def test_rf11_rf12_tm_reuse_glossary_and_hybrid_translation(tmp_path: Path) -> None:
    ctx_store = SqliteContextStore(tmp_path / "ctx.sqlite")
    ctx_store.add_glossary_term(GlossaryTerm.create("work1", "Guild", "Guilda"))
    ctx_store.add_tm_entry(
        TranslationMemoryEntry.create("work1", "en", "pt-BR", "Where is Akira?", "Onde está Akira?")
    )

    class StubNmt:
        name = "stub_nmt"

        def translate(self, text: str, packet: TranslationContextPacket) -> TranslationResult:
            if "Guild" in text:
                return TranslationResult("Ele foi para a Guilda.", 0.88)
            return TranslationResult("Traducao base", 0.8)

        def unload(self) -> None:
            return None

    class StubRefiner:
        name = "stub_refiner"

        def translate(self, text: str, packet: TranslationContextPacket) -> TranslationResult:
            return TranslationResult(text, 0.94)

        def unload(self) -> None:
            return None

    reg = TranslationRegistry()
    reg.register("nmt", StubNmt)
    assert reg.list_backends() == ["nmt"]

    doc = _make_transcribed_doc(tmp_path)
    doc_store = DocumentStore(tmp_path / "docs")
    engine = HybridTranslationEngine(primary_backend=reg.create("nmt"), refiner_backend=StubRefiner())
    uc = TranslatePageUseCase(ctx_store, ContextManager(ctx_store), engine, doc_store)

    translated_doc = uc.execute(doc, "work1", "ch2", "en", "pt-BR", persist=True)
    s1, s2 = translated_doc.text_blocks[0].sentences
    assert s1.translation == "Onde está Akira?"  # Reused from TM
    assert s2.translation == "Ele foi para a Guilda."  # Glossary term respected
    assert s2.translation_needs_review is False
    # New translation persisted in TM
    assert len(ctx_store.list_tm_entries("work1", "en", "pt-BR")) == 2


def test_rf12_rf13_missing_glossary_flag_and_manual_revision(tmp_path: Path) -> None:
    ctx_store = SqliteContextStore(tmp_path / "ctx.sqlite")
    ctx_store.add_glossary_term(GlossaryTerm.create("work1", "Guild", "Guilda"))

    class BadBackend:
        name = "bad"

        def translate(self, text: str, packet: TranslationContextPacket) -> TranslationResult:
            return TranslationResult("Ele foi para a Associacao.", 0.7)  # Violates glossary

        def unload(self) -> None:
            return None

    doc = _make_transcribed_doc(tmp_path)
    engine = HybridTranslationEngine(primary_backend=BadBackend())
    uc = TranslatePageUseCase(ctx_store, ContextManager(ctx_store), engine)
    uc.execute(doc, "work1", "ch2", "en", "pt-BR", persist=False)

    s2 = doc.text_blocks[0].sentences[1]
    assert s2.translation_needs_review is True

    review = ReviewRegionsUseCase()
    review.update_sentence_translation(doc, s2.id, "Ele foi para a Guilda.", note="Glossary fix")
    assert s2.translation == "Ele foi para a Guilda."
    assert s2.translation_needs_review is False
    assert s2.manual_override is True

    review.revert_last_revision(doc)
    assert s2.translation == "Ele foi para a Associacao."
