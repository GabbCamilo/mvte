## ADDED Requirements

### Requirement: Ingestão Somente-Leitura de Arquivos CBZ/ZIP (TRN-01)
O sistema SHALL extrair páginas de arquivos `.cbz`/`.zip` e imagens soltas sem modificar os arquivos de origem e sem criar acoplamento com o MAM.

#### Scenario: Extração com deduplicação e split train/val
- **WHEN** `ingest_archives` processa um diretório contendo arquivos `.cbz` e imagens duplicadas
- **THEN** o sistema extrai páginas únicas para `datasets/custom/images/{train,val}` preservando os arquivos originais intactos.

### Requirement: Pré-rotulagem Estruturada em Formato YOLO (TRN-02)
O sistema SHALL gerar pré-anotações normalizadas em formato YOLO para revisão humana e treinamento supervisionado.

#### Scenario: Exportação de rótulos normalizados
- **WHEN** `prelabel_dataset` executa sobre o conjunto extraído
- **THEN** o sistema gera um arquivo `.txt` por imagem com linhas `<class_id> <cx> <cy> <w> <h>` normalizadas em `[0, 1]` e um `dataset.yaml` válido.

### Requirement: Treinamento Isolado e Exportação ONNX (TRN-03)
O sistema SHALL executar treinamento em ambiente isolado e exportar pesos compatíveis com o runtime ONNX do MVTE.

#### Scenario: Exportação para ONNX após treino
- **WHEN** o pipeline de treinamento conclui as épocas configuradas
- **THEN** o melhor checkpoint é exportado para `.onnx` em `models/` sem exigir `torch` ou `ultralytics` no runtime principal do MVTE.
