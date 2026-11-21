# ocr-linguistic Specification

## Purpose
TBD - created by archiving change mvte-phase2-ocr-linguistic. Update Purpose after archive.

## Requirements

### Requirement: Reconhecimento Multilíngue e Orientação de Escrita (RF-06)
O sistema SHALL reconhecer texto em múltiplos idiomas e orientações (horizontal e vertical) utilizando backends locais substituíveis.

#### Scenario: Reconhecimento de texto horizontal e vertical
- **WHEN** regiões visuais contendo texto horizontal ou vertical são submetidas ao subsistema de OCR
- **THEN** o sistema identifica a orientação dominante (`horizontal` ou `vertical`), preserva pontuação e retorna linhas reconhecidas com coordenadas e confiança.

#### Scenario: Substituição de backend de OCR
- **WHEN** a configuração seleciona outro adaptador registrado para o idioma de origem
- **THEN** o sistema executa a transcrição mantendo o mesmo formato de saída no domínio.

### Requirement: Hierarquia Linguística e Rastreabilidade (RF-07)
O sistema SHALL representar o texto extraído em uma hierarquia estruturada vinculada às regiões visuais de origem.

#### Scenario: Construção da hierarquia completa
- **WHEN** o pipeline de OCR e reconstrução linguística processa um `PageDocument`
- **THEN** cada transcrição é estruturada na hierarquia `Page → Panel → VisualRegion → TextBlock → Sentence → Token`
- **AND** cada elemento preserva identificador único, coordenadas de origem e referência à `VisualRegion` correspondente.

### Requirement: Agrupamento de Linhas e Reconstrução de Frases (RF-08)
O sistema SHALL agrupar linhas e fragmentos próximos em frases completas, evitando tratar cada caixa de OCR como uma frase independente.

#### Scenario: Reconstrução de frase dividida em múltiplas linhas
- **WHEN** um único balão ou caixa narrativa contém múltiplas linhas pertencentes à mesma sentença
- **THEN** o subsistema de análise linguística agrupa as linhas na ordem de leitura adequada em um único `Sentence` coerente.

### Requirement: Detecção de Possíveis Erros de OCR e Revisão (RF-09)
O sistema SHALL sinalizar possíveis erros de OCR e permitir correção manual rastreável das transcrições.

#### Scenario: Sinalização de baixa confiança e correção manual
- **WHEN** uma linha ou token apresenta confiança abaixo do limiar configurado ou padrão anômalo
- **THEN** o sistema marca o elemento com alerta de revisão de OCR (`needs_review`)
- **AND** qualquer correção manual do texto é registrada em `RevisionEntry` permitindo reversão.
