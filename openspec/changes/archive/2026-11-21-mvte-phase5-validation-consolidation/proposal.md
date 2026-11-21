# Proposal: mvte-phase5-validation-consolidation

## Why
As Fases 1 a 4 implementaram todos os subsistemas de visão, OCR, tradução contextual, limpeza e renderização. Para consolidar o MVTE como um motor confiável, reproduzível e pronto para futura integração desacoplada com o Manga Archive Manager (MAM), a Fase 5 introduz a validação global automatizada, execução em lotes, benchmarks de desempenho E2E e contratos formais de integração.

## What Changes
- **Módulo `validation/`:** `PageValidationEngine` avaliando qualidade de OCR, omissões e flags de tradução, integridade de máscaras, sobreposição de caixas tipográficas e estouro de encaixe, produzindo `ValidationReport` estruturado.
- **Aplicação (`batch_pipeline.py`):** `FullPagePipeline` e `BatchRunner` executando o pipeline completo (Fases 1→5) sobre múltiplas páginas com isolamento de falhas por página, persistência e métricas de tempo.
- **Contratos de Integração (`interfaces/contracts/` + `docs/integrations/`):** DTOs versionados (`TranslationJobRequest` / `TranslationJobResponse`) e documentação técnica para execução como processo/serviço independente, sem qualquer acoplamento ao MAM.
- **Testes E2E e Desempenho:** Testes de validação, lote e latência em `tests/unit/test_phase5_validation_batch.py` e `tests/benchmarks/test_e2e_performance.py`.

## Out-of-Scope
- Implementação de código dentro do repositório do Manga Archive Manager (MAM).
