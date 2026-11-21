# Proposal: mvte-phase3-contextual-translation

## Why
A Fase 2 estruturou o texto extraído na hierarquia `Page → Panel → VisualRegion → TextBlock → Sentence → Token`. Traduzir frases isoladamente compromete pronomes, registros de fala, continuidade narrativa e terminologia da obra. A Fase 3 introduz o gerenciamento de contexto em três escalas (Micro, Meso e Macro), memória de tradução e glossário locais em SQLite, além da orquestração de tradução híbrida 100% local.

## What Changes
- **Domínio:** Entidades `TranslationEntry`, `GlossaryTerm`, `TranslationContextPacket` (Micro/Meso/Macrocontexto) e portas `ContextManagerPort`, `TranslatorBackendPort` e `HybridTranslatorPort`.
- **Infraestrutura (`infrastructure/persistence/`):** Repositório SQLite local (`ContextStore`) para glossários, memória de tradução e histórico narrativo por obra/capítulo.
- **Módulo `context_management/`:** Construtor e recuperador seletivo de contexto em 3 escalas (Micro: frase/expressão; Meso: sequência de diálogos da página; Macro: glossário, personagens e eventos anteriores relevantes).
- **Módulo `translation/`:** Orquestrador híbrido local (`HybridTranslationEngine`) combinando tradução base (`NmtBackendPort` / `CTranslate2Adapter`) e revisão/desambiguação contextual (`ContextualLlmPort` / `LlamaCppAdapter`), com registro de backends substituíveis e verificação anti-alucinação/omissão.
- **Aplicação & Revisão:** `TranslatePageUseCase` integrado ao `ModelLifecycleManager`, extensão de `ReviewRegionsUseCase` para revisão manual de traduções e testes automatizados.

## Out-of-Scope
- Limpeza de texto original, inpainting, análise tipográfica e renderização visual (Fase 4).
- Chamadas obrigatórias a APIs em nuvem.
