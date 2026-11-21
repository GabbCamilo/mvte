# Proposal: mvte-phase4-cleaning-rendering

## Why
Com as Fases 1 a 3 concluídas, o MVTE já interpreta a página, extrai o texto em hierarquia linguística e produz traduções contextuais locais. A Fase 4 implementa a remoção não destrutiva do texto original, a reconstrução seletiva de fundos (inspirada nas melhores práticas do PanelCleaner), a análise/correspondência tipográfica local e a composição visual final preservando as dimensões e a qualidade da imagem original.

## What Changes
- **Domínio (`domain/models/rendering.py`, `domain/ports/rendering.py`):** Entidades `FontMatch`, `TypographyPlan`, `RenderedLayerSpec`, `ReconstructionResult` e portas `InpainterPort`, `TextCleanerPort`, `TypographyEnginePort`, `PageCompositorPort`.
- **Módulo `text_cleaning/`:** Limpeza seletiva baseada em uniformidade de borda da máscara de caracteres (`border_std_dev`), aplicando preenchimento uniforme em balões limpos e inpainting seletivo (`OpenCvTeleaInpainter` / adaptador `LamaInpainter`) apenas em fundos complexos/ilustrações, preservando sempre o arquivo original.
- **Módulo `typography/`:** Catálogo local de fontes (Windows/Linux), correspondência por atributos visuais (peso, inclinação, largura) sem afirmar recuperação da fonte exata, cálculo de área útil interna da região e ajuste progressivo (tamanho, quebra de linhas, espaçamento, fonte alternativa, sinalização manual) sem nunca cortar ou ocultar palavras.
- **Módulo `rendering/`:** Compositor em camadas combinando imagem original, imagem limpa, máscaras e texto traduzido com exportação sem perda.
- **Aplicação & Testes:** `ReconstructPageUseCase` e testes unitários/benchmarks de qualidade visual e encaixe tipográfico.

## Out-of-Scope
- Validação global automatizada e processamento em lotes / contratos de serviço para integração futura (Fase 5).
