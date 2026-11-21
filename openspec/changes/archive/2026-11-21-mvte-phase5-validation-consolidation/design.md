# Design: mvte-phase5-validation-consolidation

## Subsistemas e Contratos
- `modules/validation/validator.py`:
  - `ValidationSeverity` (`info`, `warning`, `error`)
  - `ValidationIssue(code, target_id, severity, message)`
  - `ValidationReport(document_id, passed, issues, metrics)`
  - `PageValidationEngine.validate(document, reconstruction_result) -> ValidationReport`
- `application/use_cases/batch_pipeline.py`:
  - `FullPagePipeline`: compõe `AnalyzePageUseCase → TranscribePageUseCase → TranslatePageUseCase → ReconstructPageUseCase → PageValidationEngine`.
  - `BatchRunner`: itera sobre caminhos de imagem, captura exceções por página em `BatchItemResult`, coleta duração em ms e gera `BatchSummary`.
- `interfaces/contracts/service_contract.py`:
  - `TranslationJobRequest` / `TranslationJobResponse` (dataclasses JSON-friendly) + `execute_job(request)`.
- `docs/integrations/mam-integration-contract.md`:
  - Documenta contrato CLI/Python/JSON, variável `MVTE_MODELS_DIR` e garantias de desacoplamento.
