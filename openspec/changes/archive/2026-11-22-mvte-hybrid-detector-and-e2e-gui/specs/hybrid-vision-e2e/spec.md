## ADDED Requirements

### Requirement: Detector Híbrido em Comitê (HYB-01)
O sistema SHALL combinar detecções do modelo customizado (`Yolo11OnnxDetector`) com detecções complementares de texto livre/SFX (`RtDetrOnnxDetector`) sem duplicação excessiva.

#### Scenario: Mesclagem de detecções sem sobreposição duplicada
- **WHEN** `HybridEnsembleDetector.detect()` processa uma página
- **THEN** o sistema preserva as detecções de balão e texto em balão do detector primário e adiciona `text_free` do detector secundário apenas quando não houver sobreposição relevante (`IoU < 0.35`).

### Requirement: Refinamento de Máscara de Caracteres Estilo PanelCleaner (HYB-02)
O sistema SHALL suportar refinamento pixel a pixel da máscara de caracteres via modelo ONNX de segmentação de texto quando disponível.

#### Scenario: Refino de máscara de caracteres com fallback seguro
- **WHEN** `MaskSegmenter` processa regiões com o refinador neural disponível (ou sem ele)
- **THEN** o sistema gera máscaras de caracteres restritas à região estrutural sem alterar o formato de saída do domínio.

### Requirement: Fluxo Completo de Limpeza e Reconstrução na GUI (HYB-03)
O sistema SHALL permitir executar limpeza e composição diretamente na GUI alternando a visualização entre análise, página limpa e página reconstruída.

#### Scenario: Reconstrução visual na GUI
- **WHEN** o usuário aciona a reconstrução visual na `PageReviewWindow`
- **THEN** o sistema limpa os textos originais preservando o arquivo fonte e exibe o resultado reconstruído na janela.
