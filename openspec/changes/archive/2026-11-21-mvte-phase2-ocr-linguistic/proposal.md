# Proposal: mvte-phase2-ocr-linguistic

## Why
A Fase 1 entregou a representação visual estruturada da página (`PageDocument` com painéis, regiões visuais, máscaras e associações). Para que o MVTE compreenda o conteúdo textual antes da tradução contextual (Fase 3), é necessário extrair texto de forma estruturada, preservando orientação (horizontal/vertical), pontuação, relações sintáticas e vínculo com as coordenadas originais.

## What Changes
- **Domínio:** Extensão do `PageDocument` com as entidades `TextBlock`, `Sentence` e `Token`, consolidando a hierarquia `Page → Panel → VisualRegion → TextBlock → Sentence → Token`, além das portas `OcrBackendPort` e `LinguisticReconstructorPort`.
- **Módulo `ocr/`:** Adaptadores locais substituíveis para reconhecimento multilíngue horizontal e vertical (`RapidOcrAdapter` via ONNX Runtime, `MangaOcrAdapter` opcional para japonês e `OcrRegistry`).
- **Módulo `linguistic_analysis/`:** Agrupamento de linhas em blocos/frases completas, detecção de idioma/orientação, ordenação de leitura intra-região/painel, sinalização de possíveis erros de OCR e revisão manual rastreável.
- **Aplicação & CLI:** Caso de uso `TranscribePageUseCase` integrado ao `ModelLifecycleManager` e comando CLI para transcrição estruturada + cálculo de métricas CER/WER.

## Out-of-Scope
- Tradução neural/contextual e gerenciamento de contexto (Fase 3).
- Limpeza de texto, inpainting e renderização tipográfica (Fase 4).
