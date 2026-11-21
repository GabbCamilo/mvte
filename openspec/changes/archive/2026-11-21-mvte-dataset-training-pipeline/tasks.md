# Tasks: mvte-dataset-training-pipeline

- [x] 1.1 Criar ambiente isolado `.venv-train` com PyTorch CUDA e Ultralytics.
- [x] 1.2 Implementar `tools/training/ingest_archives.py` (extração somente-leitura, deduplicação e split `train/val`).
- [x] 1.3 Implementar `tools/training/prelabel_dataset.py` (comitê `RtDetrOnnxDetector` + `RapidOCR` gerando YOLO `.txt` + `dataset.yaml`).
- [x] 1.4 Implementar `tools/training/train_detector.py` (treino compatível com 4 GB VRAM e exportação ONNX).
- [x] 1.5 Implementar testes unitários em `tests/unit/test_training_pipeline.py` e validar `pytest -v` + `openspec validate`.
- [x] 1.6 Executar extração + pré-rotulagem inicial controlada sobre amostra do acervo e apresentar relatório ao usuário.
