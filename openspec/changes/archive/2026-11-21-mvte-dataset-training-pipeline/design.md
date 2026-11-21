# Design: mvte-dataset-training-pipeline

- **Isolamento de Ambiente:** `.venv-train` concentra `torch` (CUDA), `torchvision`, `ultralytics` e `onnx`, mantendo `.venv` leve com `onnxruntime`.
- **Pipeline em 3 Estágios (`tools/training/`):**
  1. `ingest_archives.py`: lê `.cbz`/`.zip`/`.png`/`.jpg`/`.webp`, calcula SHA-256 para evitar páginas duplicadas, redimensiona apenas se exceder limite extremo opcional (ou mantém resolução nativa) e distribui em `images/train` e `images/val`.
  2. `prelabel_dataset.py`: usa `RtDetrOnnxDetector` (classes `0: speech_balloon`, `1: text_bubble`, `2: text_free`) + `RapidOCR` text-det (para capturar texto livre/SFX não coberto) com deduplicação por IoU e grava `labels/train/*.txt`, `labels/val/*.txt` e `dataset.yaml`.
  3. `train_detector.py`: invoca `YOLO(base_model).train(data=dataset_yaml, imgsz=640, batch=4, epochs=..., device=...)` e exporta `format="onnx"` para `models/mvte-custom-detector.onnx`.
