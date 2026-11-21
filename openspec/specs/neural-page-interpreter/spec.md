# neural-page-interpreter Specification

## Purpose
TBD - created by archiving change mvte-neural-page-interpreter. Update Purpose after archive.

## Requirements

### Requirement: Separação de Painéis com Bleed por Vales de Margem (RF-21)
O sistema SHALL separar painéis em páginas reais mesmo quando personagens ou balões cruzam as margens entre quadros (*bleed*).

#### Scenario: Página multi-painel com bleed
- **WHEN** uma página possui múltiplos quadros separados por margens brancas interrompidas por elementos gráficos
- **THEN** o analisador de página identifica os painéis distintos por divisão recursiva de vales e os ordena conforme `ReadingDirection`.

### Requirement: Detecção Neural de Balões e Regiões Textuais via ONNX (RF-22)
O sistema SHALL detectar balões e blocos de texto (incluindo texto claro em fundo escuro) usando modelo neural local via ONNX Runtime sem gerar falsos positivos em ilustrações.

#### Scenario: Detecção com modelo RT-DETRv2 ONNX
- **WHEN** o modelo `comic-text-and-bubble-detector_int8.onnx` está disponível localmente
- **THEN** o detector retorna apenas balões (`speech_balloon`) e regiões textuais (`text_bubble` / `free_text`) acima do limiar de confiança, aplicando NMS e preservando coordenadas na imagem original.
