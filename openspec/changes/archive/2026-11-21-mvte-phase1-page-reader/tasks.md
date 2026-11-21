# Tasks: mvte-phase1-page-reader

## 1. Fundação do Projeto
- [x] 1.1 Criar `pyproject.toml`, `.gitignore` e `README.md` base com grupos opcionais (`cpu`, `directml`, `cuda`, `gui`, `dev`).
- [x] 1.2 Implementar entidades de domínio (`PageDocument`, `Panel`, `VisualRegion`, `MaskLayer`, `RevisionEntry`) e portas (`domain/ports/vision.py`).
- [x] 1.3 Implementar persistência sem perda e carregamento de imagem preservando o original (`infrastructure/storage/document_store.py`).

## 2. Subsistemas de Visão da Fase 1
- [x] 2.1 Implementar executor ONNX Runtime multi-backend (`infrastructure/inference/onnx_runner.py`) e `ModelLifecycleManager`.
- [x] 2.2 Implementar `modules/page_analysis/` (detecção de painéis e ordem de leitura RTL/LTR).
- [x] 2.3 Implementar `modules/visual_detection/` com adaptador substituível (ex.: detector ONNX de balões/caixas/texto e baseline morfológico).
- [x] 2.4 Implementar `modules/segmentation/` com produção de máscaras poligonais e de pixel separando estrutura visual e caracteres.
- [x] 2.5 Implementar `modules/text_association/` para associação espacial texto-estrutura e detecção de texto livre.

## 3. Aplicação, Visualização e Revisão Manual
- [x] 3.1 Implementar caso de uso `analyze_page` e `review_regions` com histórico de alterações.
- [x] 3.2 Implementar comando CLI de inspeção e exportação de overlays/máscaras (`mvte`).
- [x] 3.3 Implementar visualizador GUI (PySide6) desacoplado para inspeção de máscaras e correção manual de regiões/associações (`mvte-gui`).

## 4. Testes e Validação
- [x] 4.1 Reunir conjunto inicial de páginas reais com licença verificada em `examples/` / `tests/benchmarks/`.
- [x] 4.2 Implementar testes unitários de domínio, associação geométrica e serialização (`pytest`).
- [x] 4.3 Implementar testes de regressão de métricas (Precision/Recall/F1 de detecção e IoU/Dice de segmentação) e validar contra os critérios da spec.
