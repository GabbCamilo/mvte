# Design: mvte-hybrid-detector-and-e2e-gui

- `modules/visual_detection/detector.py`: `HybridEnsembleDetector` implementa `VisualDetectorPort`, gerenciando `primary` e `secondary` e liberando ambos em `unload()`. `resolve_default_detector()` seleciona `HybridEnsembleDetector` quando ambos `mvte-custom-detector.onnx` e `comic-text-and-bubble-detector_int8.onnx` existem.
- `modules/segmentation/segmenter.py`: `CtdOnnxMaskProvider` carrega `models/comictextdetector.pt.onnx` (input `1024x1024`) para gerar máscara global de caracteres e intersecta com cada `VisualRegion` (fallback para Otsu interior se o peso não existir).
- `interfaces/gui/main.py`: Adiciona botão **"Limpar e Reconstruir (Preview)"** e seletor de camada (`Overlay` / `Limpa` / `Reconstruída`) na `PageReviewWindow`.
