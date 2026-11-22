# Tasks: mvte-hybrid-detector-and-e2e-gui

- [x] 1.1 Baixar `comictextdetector.pt.onnx` para `models/` e inspecionar sua assinatura ONNX.
- [x] 1.2 Implementar `HybridEnsembleDetector` e atualizar `resolve_default_detector()`.
- [x] 1.3 Implementar `CtdOnnxMaskProvider` no `MaskSegmenter` (estilo PanelCleaner).
- [x] 1.4 Implementar `tools/training/benchmark_detectors.py` e rodar comparativo em páginas reais de `datasets/custom/images/val`.
- [x] 1.5 Atualizar `PageReviewWindow` (`interfaces/gui/main.py`) com botão de limpeza/reconstrução e seletor de camadas.
- [x] 1.6 Adicionar testes unitários, rodar `pytest -v`, arquivar no OpenSpec e enviar ao GitHub.
