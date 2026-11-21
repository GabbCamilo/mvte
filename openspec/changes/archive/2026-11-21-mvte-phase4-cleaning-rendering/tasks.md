# Tasks: mvte-phase4-cleaning-rendering

## 1. Domínio e Portas
- [x] 1.1 Criar `src/mvte/domain/models/rendering.py` (`FontMatch`, `TypographyPlan`, `CleanedPageResult`, `ReconstructionResult`).
- [x] 1.2 Criar `src/mvte/domain/ports/rendering.py` (`InpainterPort`, `TextCleanerPort`, `TypographyEnginePort`, `PageCompositorPort`).

## 2. Subsistemas Visuais da Fase 4
- [x] 2.1 Implementar `src/mvte/modules/text_cleaning/cleaner.py` (`SelectiveTextCleaner`, `OpenCvTeleaInpainter`, `InpainterRegistry`).
- [x] 2.2 Implementar `src/mvte/modules/typography/engine.py` (`LocalFontCatalog`, `TypographyEngine` com cálculo de área útil e ajuste progressivo sem truncamento).
- [x] 2.3 Implementar `src/mvte/modules/rendering/compositor.py` (`LayeredPageCompositor` com exportação sem perda preservando dimensões originais).

## 3. Aplicação e Testes
- [x] 3.1 Implementar `ReconstructPageUseCase` em `src/mvte/application/use_cases/reconstruct_page.py`.
- [x] 3.2 Implementar testes unitários e de qualidade visual (`tests/unit/test_phase4_cleaning_rendering.py` e `tests/benchmarks/test_visual_quality.py`) cobrindo `RF-14` a `RF-17`.
- [x] 3.3 Executar `pytest -v` e validar toda a suíte.
