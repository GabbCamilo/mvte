# Proposal: mvte-neural-page-interpreter

## Why
Testes em páginas reais de mangá mostraram que a heurística morfológica inicial (`MorphologicalBalloonDetector`) gera centenas de falsos positivos em pele, roupas e interiores de letras, além de falhar em caixas escuras com texto branco, enquanto `RETR_EXTERNAL` simples funde quadros com *bleed* em um único painel `P0`.

## What Changes
- **Análise de Painéis (`page_analysis`):** Substituir/evoluir o analisador padrão para `RecursiveGutterPageAnalyzer` (divisão recursiva por vales de margem horizontal/vertical + fallback de contorno), separando quadros mesmo com *bleed*.
- **Detecção Neural ONNX (`visual_detection`):** Adicionar `RtDetrOnnxDetector` compatível com `ogkalu/comic-text-and-bubble-detector` (`bubble`, `text_bubble`, `text_free`) via `onnxruntime`, mantendo o baseline morfológico apenas como fallback quando não houver modelo local.
- **CLI e GUI:** Selecionar automaticamente o detector neural quando `models/comic-text-and-bubble-detector_int8.onnx` estiver presente (ou via `MVTE_MODELS_DIR`), e exibir associações limpas `text_bubble → bubble → Panel` e `text_free → Panel`.

## Out-of-Scope
- Treinamento de novos pesos próprios.
