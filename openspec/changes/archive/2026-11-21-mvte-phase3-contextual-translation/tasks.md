# Tasks: mvte-phase3-contextual-translation

## 1. Domínio e Portas de Tradução/Contexto
- [x] 1.1 Criar `src/mvte/domain/models/translation.py` (`GlossaryTerm`, `TranslationMemoryEntry`, `TranslationContextPacket`, `TranslationResult`) e estender `Sentence` com campos de tradução mantendo retrocompatibilidade JSON.
- [x] 1.2 Criar `src/mvte/domain/ports/translation.py` (`ContextStorePort`, `TranslatorBackendPort`).

## 2. Persistência SQLite e Gerenciamento de Contexto
- [x] 2.1 Implementar `src/mvte/infrastructure/persistence/context_store.py` (`SqliteContextStore`) para glossário, memória de tradução e notas de macrocontexto.
- [x] 2.2 Implementar `src/mvte/modules/context_management/manager.py` (`ContextManager`) com recuperação seletiva de Micro, Meso e Macrocontexto.

## 3. Motor de Tradução Híbrida Local
- [x] 3.1 Implementar `src/mvte/modules/translation/engine.py` com `TranslationRegistry`, adaptadores locais (`CTranslate2Adapter`, `LlamaCppAdapter`) e `HybridTranslationEngine` (com verificação de glossário e completude).

## 4. Aplicação, Revisão e Testes
- [x] 4.1 Implementar `TranslatePageUseCase` e estender `ReviewRegionsUseCase` com `update_sentence_translation` e reversão.
- [x] 4.2 Implementar testes unitários e de integração cobrindo `RF-10` a `RF-13` e métricas de consistência/omissão em `tests/benchmarks/test_translation_metrics.py`.
- [x] 4.3 Executar `pytest -v` e validar toda a suíte.
