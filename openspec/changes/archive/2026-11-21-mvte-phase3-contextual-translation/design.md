# Design: mvte-phase3-contextual-translation

## Extensão do Domínio (`domain/models/linguistic.py` & `domain/models/translation.py`)
- `Sentence` recebe `translation: str = ""`, `translation_confidence: float = 0.0`, `translation_needs_review: bool = False`.
- `GlossaryTerm(id, work_id, source_term, target_term, category, notes)`
- `TranslationMemoryEntry(id, work_id, source_lang, target_lang, source_text, target_text, context_summary)`
- `TranslationContextPacket(work_id, chapter_id, source_lang, target_lang, micro_sentence, micro_tokens, meso_surrounding_sentences, macro_glossary_matches, macro_tm_matches, macro_narrative_notes)`

## Portas (`domain/ports/translation.py`)
- `ContextStorePort`: CRUD SQLite para glossário, memória de tradução e notas narrativas por `work_id`.
- `TranslatorBackendPort`: `name`, `translate(text, packet) -> TranslationResult`, `unload()`.

## Subsistemas
- `infrastructure/persistence/context_store.py`: `SqliteContextStore` (SQLite puro via `sqlite3`, zero servidor externo).
- `modules/context_management/manager.py`: `ContextManager` que constrói `TranslationContextPacket` selecionando apenas termos do glossário presentes (ou por sobreposição lexical) na frase/mesocontexto e entradas de TM relevantes.
- `modules/translation/engine.py`:
  - `TranslationRegistry`
  - `CTranslate2Adapter` (NMT local opcional)
  - `LlamaCppAdapter` (LLM GGUF local opcional via `llama-cpp-python`)
  - `HybridTranslationEngine`: combina backend primário + refinador contextual opcional + verificação de completude/terminologia (garante aplicação do glossário e sinaliza `translation_needs_review` em caso de omissão ou saída vazia).
- `application/use_cases/translate_page.py`: `TranslatePageUseCase` percorre `text_blocks` na ordem de leitura, atualiza `Sentence.translation`, grava novas entradas na TM e libera modelos ao final.
