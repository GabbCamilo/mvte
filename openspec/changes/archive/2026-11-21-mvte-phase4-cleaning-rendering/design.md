# Design: mvte-phase4-cleaning-rendering

## Arquitetura dos Subsistemas
- `modules/text_cleaning/cleaner.py`:
  - `SelectiveTextCleaner`: para cada `VisualRegion`, utiliza `character_mask` dilatada levemente (nunca o retângulo inteiro do balão), mede o desvio-padrão das bordas externas à máscara (`border_std_dev`). Se `<= uniform_threshold`, preenche com a cor mediana da borda; caso contrário, delega a região ao `InpainterPort` (`OpenCvTeleaInpainter` padrão local ou `LamaOnnxInpainter` plugável).
- `modules/typography/engine.py`:
  - `LocalFontCatalog`: descobre fontes `.ttf`/`.otf` instaladas no SO (Windows `C:\Windows\Fonts`, Linux `/usr/share/fonts`, `~/.local/share/fonts`) + diretório opcional do projeto, com fallback seguro.
  - `TypographyEngine`: calcula área útil interna a partir da `structure_mask` (maior retângulo interno inscrito aproximado por erosão/distância), estima estilo e aplica `fit_text_to_region` em etapas (tamanho → quebra de linhas → espaçamento → fonte alternativa → `needs_manual_review`).
- `modules/rendering/compositor.py`:
  - `LayeredPageCompositor`: renderiza texto com `Pillow` sobre cópia da imagem limpa (nunca sobre o original), suporta contorno/halo de legibilidade quando necessário e salva `cleaned.png` + `translated.png` preservando dimensões exatas.
- `application/use_cases/reconstruct_page.py`:
  - `ReconstructPageUseCase`: orquestra limpeza, planejamento tipográfico e composição, atualizando `document.metadata["outputs"]` e persistindo no `DocumentStore`.
