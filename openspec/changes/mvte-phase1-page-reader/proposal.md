# Proposal: mvte-phase1-page-reader

## Contexto e Objetivo
Esta proposta corresponde à **Fase 1 — Leitor Global de Páginas** do MVTE. Após a conclusão da Fase 0 (exploração e fundamentação arquitetural), o objetivo é estruturar a fundação mínima do projeto (`pyproject.toml`, camadas `domain/`, `application/`, `infrastructure/`, `modules/` da Fase 1 e interface de visualização/revisão manual) para importar uma página completa de mangá ou quadrinho e representá-la como um documento visual estruturado e rastreável.

## Escopo (In-Scope)
- Estruturação do pacote Python `mvte` com configuração de dependências para CPU e GPU (Windows e Linux).
- Modelo de domínio hierárquico (`PageDocument`, `Panel`, `VisualRegion`, `MaskLayer`) com preservação da imagem original.
- Subsistema `page_analysis`: carregamento sem perda, detecção de limites da página, identificação de painéis/quadros e estimativa de ordem de leitura.
- Subsistema `visual_detection`: detecção de balões de fala, balões de pensamento, caixas narrativas, SFX/onomatopeias e regiões de texto livre via adaptadores substituíveis.
- Subsistema `segmentation`: geração de bounding boxes, máscaras poligonais e máscaras de pixel, distinguindo máscara da estrutura visual da máscara de caracteres.
- Subsistema `text_association` (nível estrutural inicial): associação entre regiões de texto e estruturas visuais/painéis.
- Visualização das máscaras e interface de revisão manual para corrigir regiões e associações incorretas.
- Testes automatizados com páginas reais licenciadas e métricas de detecção/segmentação.

## Fora de Escopo (Out-of-Scope)
- OCR e reconstrução linguística completa (Fase 2).
- Gestão de contexto e tradução neural/contextual (Fase 3).
- Inpainting, limpeza destrutiva/não destrutiva, tipografia e renderização final (Fase 4).
- Integração com o Manga Archive Manager (MAM).
