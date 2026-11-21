"""Hybrid local translation engine (NMT + contextual local LLM + TM/glossary verification)."""

from __future__ import annotations

import gc
from pathlib import Path
from typing import Callable

from mvte.domain.models.translation import TranslationContextPacket, TranslationResult
from mvte.domain.ports.translation import TranslatorBackendPort


class CTranslate2Adapter:
    """Optional local NMT backend using CTranslate2 (CPU/CUDA INT8)."""

    name = "ctranslate2_nmt"

    def __init__(self, model_dir: Path | str, tokenizer_path: Path | str | None = None) -> None:
        self.model_dir = Path(model_dir)
        self.tokenizer_path = Path(tokenizer_path) if tokenizer_path else None
        self._translator = None
        self._sp = None

    def _load(self) -> None:
        if self._translator is not None:
            return
        import ctranslate2

        self._translator = ctranslate2.Translator(str(self.model_dir))
        if self.tokenizer_path is not None:
            import sentencepiece as spm

            self._sp = spm.SentencePieceProcessor(model_file=str(self.tokenizer_path))

    def translate(self, text: str, packet: TranslationContextPacket) -> TranslationResult:
        self._load()
        tokens = self._sp.encode(text, out_type=str) if self._sp else text.split()
        results = self._translator.translate_batch([tokens])
        out_tokens = results[0].hypotheses[0]
        translated = self._sp.decode(out_tokens) if self._sp else " ".join(out_tokens)
        return TranslationResult(translated_text=translated.strip(), confidence=0.85)

    def unload(self) -> None:
        if self._translator is not None:
            del self._translator
            self._translator = None
            self._sp = None
            gc.collect()


class LlamaCppAdapter:
    """Optional local contextual LLM backend using llama-cpp-python (GGUF)."""

    name = "llama_cpp_gguf"

    def __init__(self, model_path: Path | str, n_ctx: int = 2048, n_gpu_layers: int = -1) -> None:
        self.model_path = Path(model_path)
        self.n_ctx = n_ctx
        self.n_gpu_layers = n_gpu_layers
        self._llm = None

    def _load(self) -> None:
        if self._llm is None:
            from llama_cpp import Llama

            self._llm = Llama(
                model_path=str(self.model_path),
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                verbose=False,
            )

    def translate(self, text: str, packet: TranslationContextPacket) -> TranslationResult:
        self._load()
        glossary_hint = "; ".join(
            f"{g.source_term} -> {g.target_term}" for g in packet.macro_glossary_matches
        )
        meso_hint = " | ".join(packet.meso_surrounding_sentences)
        prompt = (
            f"Translate faithfully from {packet.source_lang} to {packet.target_lang} "
            f"without adding facts.\n"
            f"Glossary: {glossary_hint or 'none'}\n"
            f"Surrounding dialogue: {meso_hint or 'none'}\n"
            f"Text: {text}\nTranslation:"
        )
        output = self._llm(prompt, max_tokens=256, temperature=0.2, stop=["\n"])
        translated = str(output["choices"][0]["text"]).strip()
        return TranslationResult(translated_text=translated, confidence=0.9)

    def unload(self) -> None:
        if self._llm is not None:
            del self._llm
            self._llm = None
            gc.collect()


class HybridTranslationEngine:
    """Combines TM exact reuse, base NMT/translator, optional contextual refiner, and quality checks."""

    def __init__(
        self,
        primary_backend: TranslatorBackendPort,
        refiner_backend: TranslatorBackendPort | None = None,
    ) -> None:
        self.primary_backend = primary_backend
        self.refiner_backend = refiner_backend

    def translate(self, packet: TranslationContextPacket) -> TranslationResult:
        source_clean = packet.micro_sentence.strip()
        if not source_clean:
            return TranslationResult(translated_text="", confidence=1.0, needs_review=False)

        # 1. Exact Translation Memory match
        for tm in packet.macro_tm_matches:
            if tm.source_text.strip().lower() == source_clean.lower():
                return TranslationResult(
                    translated_text=tm.target_text,
                    confidence=0.99,
                    needs_review=False,
                    used_tm=True,
                )

        # 2. Primary local translation
        base_res = self.primary_backend.translate(source_clean, packet)
        final_text = base_res.translated_text.strip()
        confidence = base_res.confidence

        # 3. Optional contextual refinement / disambiguation
        if self.refiner_backend is not None and final_text:
            refined = self.refiner_backend.translate(final_text, packet)
            if refined.translated_text.strip():
                final_text = refined.translated_text.strip()
                confidence = (confidence + refined.confidence) / 2.0

        # 4. Enforce glossary consistency & detect omissions
        needs_review = False
        reasons: list[str] = []
        if not final_text:
            needs_review = True
            reasons.append("empty_translation")
        for term in packet.macro_glossary_matches:
            if term.target_term.lower() not in final_text.lower():
                needs_review = True
                reasons.append(f"missing_glossary:{term.source_term}->{term.target_term}")

        return TranslationResult(
            translated_text=final_text,
            confidence=confidence,
            needs_review=needs_review,
            review_reason="; ".join(reasons),
        )

    def unload(self) -> None:
        self.primary_backend.unload()
        if self.refiner_backend is not None:
            self.refiner_backend.unload()
        gc.collect()


class TranslationRegistry:
    """Registry for replaceable local translation backends."""

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], TranslatorBackendPort]] = {}

    def register(self, name: str, factory: Callable[[], TranslatorBackendPort]) -> None:
        self._factories[name] = factory

    def create(self, name: str) -> TranslatorBackendPort:
        if name not in self._factories:
            available = ", ".join(sorted(self._factories))
            raise KeyError(f"Unknown translator backend '{name}'. Available: {available}")
        return self._factories[name]()

    def list_backends(self) -> list[str]:
        return sorted(self._factories)
