# Design: mvte-phase2-ocr-linguistic

## Modelo de Domínio Estendido (`domain/models/page.py` & `domain/models/linguistic.py`)
- `TextOrientation` (`horizontal`, `vertical`, `unknown`)
- `Token(id, text, bbox, confidence, needs_review)`
- `Sentence(id, text, tokens, bbox, reading_order, language, confidence, needs_review, manual_override)`
- `TextBlock(id, region_id, panel_id, orientation, language, lines, sentences, reading_order)`
- `PageDocument` passa a incluir `text_blocks: list[TextBlock]` serializados em JSON mantendo compatibilidade com documentos da Fase 1.

## Portas e Subsistemas
- `domain/ports/ocr.py`:
  - `OcrLine(text, bbox, confidence, orientation)`
  - `OcrBackendPort(name, recognize(crop_bgr, orientation) -> list[OcrLine], unload())`
  - `LinguisticReconstructorPort(reconstruct(panel_id, region, ocr_lines, direction) -> TextBlock)`
- `modules/ocr/`:
  - `OcrRegistry` + `RapidOcrAdapter` (ONNX Runtime, sem `paddlepaddle`) + `MangaOcrAdapter` (opcional) + `OcrConfidenceFilter`.
- `modules/linguistic_analysis/`:
  - `SentenceReconstructor`: ordena linhas (RTL vertical vs LTR horizontal), une hifenizações/continuações sem pontuação final em `Sentence`, tokeniza preservando pontuação e sinaliza `needs_review` para baixa confiança ou caracteres anômalos.
- `application/use_cases/transcribe_page.py`:
  - `TranscribePageUseCase`: percorre `VisualRegion`s ordenadas por painel/leitura, recorta ROI sem perda, executa OCR, descarrega backend via `ModelLifecycleManager`, reconstrói `TextBlock`s e persiste no `DocumentStore`.
