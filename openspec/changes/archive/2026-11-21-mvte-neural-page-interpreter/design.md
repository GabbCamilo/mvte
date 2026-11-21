# Design: mvte-neural-page-interpreter

- `modules/page_analysis/analyzer.py`: `ContourPageAnalyzer` passa a usar divisão recursiva por vales horizontais e verticais (*Recursive XY-Cut* sobre projeções de pixels claros >= 235) antes do fallback de contorno, com limiar mínimo de tamanho de painel e ordenação RTL/LTR.
- `modules/visual_detection/detector.py`: `RtDetrOnnxDetector` carrega `detector_int8.onnx` via `OnnxSessionWrapper`, pré-processa em `640x640` (`RGB / 255.0`), decodifica `logits` (softmax/sigmoid) e `pred_boxes` (`cx, cy, w, h` normalizados), aplica NMS por classe e mapeia `0 -> SPEECH_BALLOON`, `1 -> FREE_TEXT` (texto em balão para associação), `2 -> FREE_TEXT` (texto livre / SFX / narração escura).
- `interfaces/cli/main.py` e `interfaces/gui/main.py`: `resolve_default_detector()` seleciona `RtDetrOnnxDetector` automaticamente quando o peso existe em `models/` (ou `MVTE_MODELS_DIR`), usando `MorphologicalBalloonDetector` apenas como fallback.
