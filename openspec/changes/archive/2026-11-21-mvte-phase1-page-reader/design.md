# Design: mvte-phase1-page-reader

## Arquitetura Aplicada
- **`domain/`:**
  - `models/page.py`: `PageDocument`, `Panel`, `VisualRegion`, `MaskLayer`, `RevisionEntry`.
  - `ports/vision.py`: `PageAnalyzerPort`, `VisualDetectorPort`, `SegmenterPort`, `RegionAssociatorPort`.
- **`application/`:**
  - `use_cases/analyze_page.py`: Orquestra `PageAnalyzerPort → VisualDetectorPort → SegmenterPort → RegionAssociatorPort` e gerencia o ciclo de vida dos modelos (`ModelLifecycleManager`).
  - `use_cases/review_regions.py`: Aplica edições manuais no `PageDocument` registrando `RevisionEntry`.
- **`infrastructure/`:**
  - `inference/onnx_runner.py`: Executor ONNX Runtime com seleção automática de provider (DirectML/CUDA/ROCm/CPU).
  - `storage/document_store.py`: Serialização de `PageDocument` (JSON) e máscaras (PNG sem perda) preservando a imagem original intacta.
- **`modules/`:**
  - `page_analysis/`: Detecção de painéis + ordenação RTL/LTR.
  - `visual_detection/`: Adaptadores para modelos de detecção (ex.: YOLO ONNX / Comic Text Detector ONNX).
  - `segmentation/`: Extração de polígonos (`shapely`/`pyclipper`) e máscaras de pixel.
  - `text_association/`: Associação por contenção geométrica, IoU e proximidade.
- **`interfaces/`:**
  - `cli/`: Comando para análise em lote/única e exportação de overlays de inspeção.
  - `gui/`: Visualizador PySide6 desacoplado (exibe imagem original, camadas de máscara e permite editar/reassociar regiões).

## Rastreabilidade Spec ↔ Design
- RF-01 → `domain/models/page.py` + `infrastructure/storage/document_store.py`
- RF-02 → `modules/page_analysis/`
- RF-03 → `domain/ports/vision.py` + `modules/visual_detection/` + `infrastructure/inference/onnx_runner.py`
- RF-04 → `modules/segmentation/`
- RF-05 → `modules/text_association/` + `application/use_cases/review_regions.py` + `interfaces/gui/`
