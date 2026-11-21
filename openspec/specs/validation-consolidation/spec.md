# validation-consolidation Specification

## Purpose
TBD - created by archiving change mvte-phase5-validation-consolidation. Update Purpose after archive.

## Requirements

### Requirement: Validação Global de Qualidade e Integridade (RF-18)
O sistema SHALL validar automaticamente os resultados do pipeline quanto a OCR, tradução, máscaras e encaixe tipográfico.

#### Scenario: Geração de relatório de validação com alertas
- **WHEN** um `PageDocument` processado e seus planos de reconstrução são submetidos ao `PageValidationEngine`
- **THEN** o sistema verifica erros de OCR (`needs_review`), omissões na tradução, integridade das máscaras, estouros tipográficos e sobreposições entre regiões renderizadas
- **AND** retorna um `ValidationReport` rastreável indicando aprovação ou lista de `ValidationIssue`s.

### Requirement: Processamento em Lotes com Isolamento de Falhas (RF-19)
O sistema SHALL processar lotes de páginas de forma reproduzível e isolar falhas individuais sem interromper o restante do lote.

#### Scenario: Execução de lote com página válida e página inválida
- **WHEN** o `BatchRunner` recebe um conjunto contendo páginas válidas e um arquivo corrompido
- **THEN** o sistema conclui o processamento completo das páginas válidas, registra a falha da página inválida no resumo do lote e não aborta o lote inteiro.

### Requirement: Contrato Independente para Integração Futura (RF-20)
O sistema SHALL expor contratos de entrada e saída desacoplados para execução como processo ou serviço independente.

#### Scenario: Execução via contrato de serviço sem dependências do MAM
- **WHEN** um chamador externo invoca `execute_job(TranslationJobRequest)`
- **THEN** o sistema executa o pipeline utilizando apenas modelos e configurações locais do MVTE e retorna `TranslationJobResponse` serializável com caminhos de saída e status de validação.
