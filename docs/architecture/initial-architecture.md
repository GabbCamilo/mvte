# Arquitetura Inicial do MVTE

Este documento define a arquitetura modular inicial do **Manga Vision & Translation Engine (MVTE)**, projetada para execução exclusivamente local, multiplataforma (Windows e Linux), com separação estrita de responsabilidades e independência total do Manga Archive Manager (MAM).

---

## 1. Visão Geral em Camadas

```text
+-----------------------------------------------------------------------+
|                       interfaces/ (CLI, GUI PySide6, API Local)       |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                    application/ (Orquestração & Pipelines)            |
|  - PageTranslationPipeline   - BatchRunner   - ModelLifecycleManager  |
+-----------------------------------------------------------------------+
          |                                                |
          v                                                v
+-----------------------------------+    +------------------------------+
|          domain/                  |    |       infrastructure/        |
|  - PageDocument (hierarquia)      |    |  - SQLite (TM, Glossário,    |
|  - VisualRegion, TextBlock        |    |    Histórico de Operações)   |
|  - Sentence, Token, MaskLayer     |    |  - ONNX / PyTorch / llama.cpp|
|  - Contratos (Protocols/ABCs)     |    |  - Storage & Image IO        |
+-----------------------------------+    +------------------------------+
          ^
          | implementam contratos de domain/
+-----------------------------------------------------------------------+
|                             modules/                                  |
|  1. page_analysis        7. context_management                        |
|  2. visual_detection     8. translation                               |
|  3. segmentation         9. text_cleaning                             |
|  4. text_association    10. typography                                |
|  5. ocr                 11. rendering                                 |
|  6. linguistic_analysis 12. validation                                |
+-----------------------------------------------------------------------+
```

---

## 2. Estrutura de Diretórios Proposta

```text
mvte/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── .gitignore
├── openspec/
│   ├── config.yaml
│   ├── specs/
│   ├── changes/
│   └── changes/archive/
├── docs/
│   ├── product/
│   ├── architecture/
│   ├── research/
│   ├── development/
│   └── integrations/
├── src/
│   └── mvte/
│       ├── domain/           # Entidades, hierarquia Page→Panel→Region→Block→Sentence→Token, Protocols
│       ├── application/      # Casos de uso, orquestração do pipeline, ciclo de vida de modelos
│       ├── infrastructure/   # Backends (ONNX, llama.cpp, CTranslate2), SQLite, logging, filesystem
│       ├── modules/          # Os 12 subsistemas independentes e desacoplados
│       └── interfaces/       # CLI, GUI (PySide6) e contratos de serviço/processo para futura integração
├── tests/
│   ├── unit/
│   ├── integration/
│   └── benchmarks/           # Conjuntos reais licenciados e métricas (IoU, F1, CER/WER)
├── models/                   # Manifesto/cache local de pesos (não versionados no git)
└── examples/                 # Páginas de exemplo com licença verificada
```

*Nota:* Diretórios como `datasets/`, `tools/` e `storage/` só serão criados quando houver demanda real na respectiva fase, evitando abstrações vazias.

---

## 3. Modelo de Domínio Hierárquico

Para garantir rastreabilidade ponta a ponta e evitar que caixas de OCR sejam tratadas como frases isoladas, o núcleo do domínio (`domain/`) adota a seguinte hierarquia imutável/versionada:

`PageDocument` → `Panel` → `VisualRegion` (balão de fala, pensamento, caixa narrativa, SFX, texto livre) → `TextBlock` → `Sentence` → `Token`

Cada elemento preserva:
- `id` único (UUID/determinístico),
- coordenadas de origem (`bbox`, `polygon`, referência à `MaskLayer`),
- metadados de confiança e origem (`auto` vs `manual_override`),
- histórico de revisões para auditoria e rollback.

---

## 4. Responsabilidades dos 12 Subsistemas (`modules/`)

1. **`page_analysis`:** Interpretação global da página (limites, painéis, divisões visuais, estimativa de ordem de leitura RTL/LTR e mapa de composição).
2. **`visual_detection`:** Localização de `speech_balloon`, `thought_balloon`, `narration_box`, `sfx`, `free_text`, texto vertical/inclinado e sobreposições, via adaptadores de modelo substituíveis.
3. **`segmentation`:** Geração de bounding boxes, máscaras poligonais, máscaras de pixel, contornos externos e regiões internas úteis (`largestinteriorrectangle`), distinguindo **máscara da estrutura visual** da **máscara de caracteres**.
4. **`text_association`:** Associação entre regiões de texto e estruturas visuais por proximidade, contenção geométrica, orientação e continuidade de leitura dentro do painel.
5. **`ocr`:** Reconhecimento multilíngue (horizontal e vertical) por adaptadores (`manga-ocr`, `rapidocr-onnxruntime`), preservando pontuação e coordenadas por linha.
6. **`linguistic_analysis`:** Agrupamento de linhas/palavras em `Sentence` e `Token`, preservação de relações sintáticas, detecção de expressões compostas e sinalização de possíveis erros de OCR.
7. **`context_management`:** Gestão de Microcontexto (frase/expressão), Mesocontexto (diálogo/página) e Macrocontexto (capítulo/obra/personagens) usando SQLite + recuperação seletiva de glossário e memória de tradução.
8. **`translation`:** Tradução híbrida local (NMT rápido + LLM GGUF contextual) com desambiguação, interpretação idiomática e revisão semântica sem alucinação de fatos inexistentes.
9. **`text_cleaning`:** Remoção não destrutiva do texto original usando máscaras ajustadas por uniformidade de borda (inspirado no `PanelCleaner`) e inpainting seletivo (LaMa / Telea) apenas quando o fundo exige reconstrução.
10. **`typography`:** Análise de características visuais (peso, inclinação, espaçamento, orientação), correspondência com fontes locais disponíveis e ajuste de texto sem cortes/deformações excessivas, sinalizando revisão manual quando necessário.
11. **`rendering`:** Composição em camadas (imagem original preservada, camada limpa, máscaras, texto traduzido) mantendo dimensões originais e exportando em formatos sem perda (PNG, PSD, etc.).
12. **`validation`:** Avaliação automática e suporte à revisão manual de fidelidade semântica, completude, erros de OCR, qualidade de limpeza/inpainting, legibilidade e sobreposição tipográfica.

---

## 5. Comunicação entre Componentes e Preservação de Independência do MAM

- **Comunicação Interna:** Os módulos não se importam diretamente entre si; comunicam-se exclusivamente através de **DTOs/Entidades do `domain/`** e **Interfaces (`Protocol`)** orquestradas pela camada `application/`.
- **Execução Local e Gerenciamento de VRAM:** O `ModelLifecycleManager` em `application/` garante que apenas os modelos da etapa ativa residam na VRAM, permitindo rodar em GPUs de 4 GB a 8 GB.
- **Independência do MAM (Manga Archive Manager):**
  - O MVTE não importa nem referencia nenhum módulo, schema ou dependência do MAM.
  - O contrato público futuro residirá em `src/mvte/interfaces/contracts/` (CLI JSON/stdin-stdout, Python API limpa ou serviço IPC/HTTP local opcional), recebendo caminhos/bytes de imagem + configuração de idioma/contexto e retornando o `PageDocument` serializado + camadas renderizadas.
  - Os modelos baixados em `models/` podem ser compartilhados via configuração de caminho (`MVTE_MODELS_DIR`), sem acoplamento de código.

---

## 6. Estratégia de Testes e Métricas de Aceitação

- **Conjuntos Reais Licenciados:** Construir suite de referência com páginas sob licenças permissivas/domínio público (ex.: obras em domínio público, Creative Commons ou datasets acadêmicos autorizados como páginas permitidas do Comic/Manga benchmarks) cobrindo os 10 cenários críticos (balões simples/irregulares, texto vertical, onomatopeias, caixas narrativas, texto sobre ilustração, balões sobrepostos, múltiplas frases, baixa legibilidade, múltiplos idiomas).
- **Métricas Monitoradas por Fase:**
  - Detecção: Precision, Recall, F1.
  - Segmentação: IoU e Dice.
  - OCR: CER (Character Error Rate) e WER (Word Error Rate).
  - Associação & Leitura: Taxa de erros de associação e taxa de omissões.
  - Tradução: Fidelidade semântica, consistência terminológica e taxa de omissões.
  - Limpeza & Tipografia: PSNR/SSIM ou inspeção de bordas pós-inpainting e taxa de encaixe tipográfico sem overflow/corte.
