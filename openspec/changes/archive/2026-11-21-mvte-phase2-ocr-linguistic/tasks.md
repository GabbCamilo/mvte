# Tasks: mvte-phase2-ocr-linguistic

## 1. Domínio Linguístico e Portas
- [x] 1.1 Criar `src/mvte/domain/models/linguistic.py` (`TextOrientation`, `Token`, `Sentence`, `TextBlock`) e integrar `text_blocks` ao `PageDocument` mantendo retrocompatibilidade JSON.
- [x] 1.2 Criar `src/mvte/domain/ports/ocr.py` (`OcrLine`, `OcrBackendPort`, `LinguisticReconstructorPort`).

## 2. Subsistemas OCR e Reconstrução Linguística
- [x] 2.1 Implementar `src/mvte/modules/ocr/backends.py` com `OcrRegistry`, detector de orientação (`horizontal`/`vertical`) e adaptadores locais (`RapidOcrAdapter` ONNX e `MangaOcrAdapter` opcional).
- [x] 2.2 Implementar `src/mvte/modules/linguistic_analysis/reconstructor.py` para agrupamento de linhas em frases completas, tokenização preservando pontuação, ordenação de leitura e sinalização de possíveis erros de OCR (`needs_review`).

## 3. Aplicação, Revisão e CLI
- [x] 3.1 Implementar `TranscribePageUseCase` com gerenciamento de ciclo de vida de modelos e persistência no `DocumentStore`.
- [x] 3.2 Estender `ReviewRegionsUseCase` com revisão manual rastreável de transcrições (`update_sentence_text` + `revert_last_revision`).
- [x] 3.3 Adicionar subcomando/opção na CLI para transcrição estruturada (`--transcribe`).

## 4. Testes e Métricas (CER / WER)
- [x] 4.1 Implementar testes unitários e de integração cobrindo `RF-06` a `RF-09` (orientação horizontal/vertical, backend substituível, hierarquia completa, agrupamento multilinha e revisão manual).
- [x] 4.2 Implementar benchmark de métricas `CER` e `WER` em `tests/benchmarks/test_ocr_metrics.py` e validar toda a suíte `pytest`.
