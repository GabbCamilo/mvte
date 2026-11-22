# Proposal: mvte-hybrid-detector-and-e2e-gui

## Why
O modelo customizado `mvte-custom-detector.onnx` atingiu `98.5% mAP50` em `speech_balloon` e `98.4% mAP50` em `text_bubble`, enquanto o modelo pré-treinado `comic-text-and-bubble-detector_int8.onnx` e o `comictextdetector.pt.onnx` (base do PanelCleaner) oferecem forte cobertura complementar em `text_free`/SFX e máscara pixel a pixel de caracteres.

## What Changes
- **Benchmark Comparativo (`tools/training/benchmark_detectors.py`):** Compara `Yolo11OnnxDetector`, `RtDetrOnnxDetector` e `HybridEnsembleDetector` em páginas reais do conjunto de validação.
- **Detector Híbrido (`HybridEnsembleDetector`):** Combina `mvte-custom-detector.onnx` (`speech_balloon` + `text_bubble`) com complemento `text_free` do `RtDetrOnnxDetector`.
- **Segmentação Fina (`ComicTextMaskRefiner`):** Usa `comictextdetector.pt.onnx` (quando presente em `models/`) para refinar a máscara pixel a pixel de caracteres ao estilo PanelCleaner, preservando ilustrações e bordas.
- **GUI E2E (`PageReviewWindow`):** Adiciona ação para executar limpeza seletiva + composição tipográfica e alternar visualização entre **Overlay**, **Limpa** e **Traduzida**.

## Out-of-Scope
- Chamadas a APIs externas em nuvem.
