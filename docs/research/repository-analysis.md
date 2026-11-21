# Análise dos Repositórios de Referência

Este documento apresenta a análise técnica individual, matriz comparativa e estratégia de reutilização dos cinco repositórios de referência investigados para o **MVTE (Manga Vision & Translation Engine)**. Todas as informações foram verificadas diretamente nos repositórios clonados (ou nas tentativas de acesso direto).

---

## 1. Análise Individual

### 1.1. Comic Text Detector
- **URL informada:** `https://github.com/misha-wu/comic-text-detector` (fork/espelho compatível com o upstream `dmMaze/comic-text-detector`)
- **Último commit observado:** `2024-04-23` (`refactoring imports`)
- **Licença:** **GPL-3.0** (`GNU General Public License v3.0`)
- **Linguagem e Frameworks:** Python, PyTorch (`>=1.7.0`), ONNX (`>=1.9.0`), `onnx-simplifier`, OpenCV (`>=4.1.2`), Pillow (`>=7.1.2`), NumPy.
- **Arquitetura Interna:**
  - `basemodel.py` e `inference.py` (`TextDetector`): combina detecção de blocos via **YOLOv5** (`models/yolov5/`), segmentação de máscara de texto via **U-Net** e detecção de linhas de texto via **DBNet** (`utils/db_utils.py` — `SegDetectorRepresenter`).
  - `utils/textblock.py` (`TextBlock`, `group_output`): agrupa linhas de texto em blocos, estima orientação (horizontal/vertical) e idioma grosseiro (`eng`, `ja`, `unknown`).
  - `utils/textmask.py` (`refine_mask`, `refine_undetected_mask`): refina máscaras para inpainting (`REFINEMASK_INPAINT`) ou anotação (`REFINEMASK_ANNOTATION`).
  - Suporta inferência em `.pt` (PyTorch) e `.onnx` (via `TextDetBaseDNN` / OpenCV DNN).
- **Entradas e Saídas:** Imagem BGR (`np.ndarray`) → `(mask, mask_refined, blk_list)` com `xyxy`, polígonos de linhas (`lines`), e máscara binária/probabilística.
- **Compatibilidade (Windows/Linux) e Hardware:** Multiplataforma (Python + PyTorch/ONNX/OpenCV). Leve para inferência em `1024x1024`; roda em CPU e GPU.
- **Limitações Conhecidas:**
  - Não detecta painéis/quadros nem ordem de leitura global.
  - Não distingue balões de fala, balões de pensamento, caixas narrativas e SFX.
  - Licença GPL-3.0 exige compatibilidade copyleft se o código-fonte for incorporado diretamente.
- **Estratégia para o MVTE:** Não copiar o repositório inteiro. Utilizar como referência de pipeline híbrido (detecção de bloco + máscara de texto + linhas DBNet) e construir adaptadores limpos para execução via ONNX Runtime (evitando acoplamento direto ao código GPL-3.0 e permitindo substituição do modelo).

---

### 1.2. Manga-Segment
- **URL:** `https://github.com/Ashu11-A/Manga-Segment`
- **Último commit observado:** `2026-06-19` (`Add copyright disclaimer to README`)
- **Licença:** **AGPL-3.0** (`GNU Affero General Public License v3.0`) — **Risco jurídico crítico.**
- **Linguagem e Frameworks:** Python `>=3.12` (gerenciado com `uv`), PyTorch `>=2.11.0`, Ultralytics YOLO `>=8.4.33` (YOLOv8, YOLOv11, YOLOv26), TensorFlow `>=2.17` (para U-Net), OpenCV, Flask (proxy HTTP), Roboflow.
- **Arquitetura Interna:**
  - `src/core/segmenter.py`: define `BaseSegmenter` (Template Method com `predict(image_bgr) -> SegmentationResult`), `Instance(label, mask)` e `SegmentationResult`.
  - `src/algorithms/yolo/` e `src/algorithms/unet/`: backends plugáveis registrados via `core/registry.py`.
  - `src/dataset/`: scripts de destilação com `ctd_teacher.py`, `paddleocr_teacher.py` e `ensemble_teacher.py`.
  - Taxonomia de classes (dataset v0.3): painéis (`comic`), `speech-balloon`, `thought-balloon`, `caption-box` e `text`.
- **Conflito de Dependências Documentado:** O próprio `pyproject.toml` registra que `paddlepaddle` fixa `protobuf <=3.20.2`, sendo incompatível com `tensorflow` (`protobuf >=3.20.3`), exigindo ambientes isolados (`src/dataset/run.py`).
- **Limitações Conhecidas:**
  - Licença **AGPL-3.0** impõe obrigação de abertura de código-fonte caso o sistema seja exposto como serviço em rede (impactando futura integração via serviço com o MAM se houvesse reutilização de código).
  - Stack duplo pesado (PyTorch + TensorFlow no mesmo ambiente).
  - Não realiza OCR, associação texto-balão, ordem de leitura, tradução ou inpainting.
- **Estratégia para o MVTE:** **Não reutilizar código-fonte** devido à licença AGPL-3.0 e ao acoplamento TF+PyTorch. Adotar apenas os conceitos arquiteturais (padrão `BaseSegmenter` / `SegmentationResult` e taxonomia de classes visuais) em implementação própria do MVTE.

---

### 1.3. Panel Cleaner
- **URL:** `https://github.com/VoxelCubes/PanelCleaner`
- **Último commit observado:** `2026-07-16` (`Update flatpak metadata`) — projeto ativo e bem mantido.
- **Licença:** **GPL-3.0-or-later**
- **Linguagem e Frameworks:** Python `>=3.10`, PyTorch, TorchVision, OpenCV, Pillow, `shapely`, `pyclipper`, `scipy`, `simple_lama_inpainting`, `manga_ocr`, `pytesseract`, `psd-tools >= 1.11.0`, `PySide6` (separado do núcleo CLI em `setup-cli.cfg` vs `setup-cli-gui.cfg`).
- **Arquitetura Interna:**
  - `pcleaner/ctd_interface.py`: interface isolada com uma versão enxuta do `comic_text_detector` (único ponto de acoplamento com o CTD).
  - `pcleaner/preprocessor.py`: pré-processamento e filtragem opcional por OCR (`manga_ocr` / `pytesseract`) para ignorar balões com apenas símbolos/números.
  - `pcleaner/masker.py`: estratégia avançada de ajuste de máscaras (`ops.pick_best_mask`) — gera máscaras com diferentes espessuras dentro da interseção da caixa estendida com a máscara precisa e escolhe a de menor desvio-padrão de borda (*border uniformity*).
  - `pcleaner/denoiser.py`: limpa ruídos residuais em caixas com alta variação de borda, ignorando imagens 1-bit.
  - `pcleaner/inpainting.py`: utiliza `SimpleLama` **seletivamente** apenas nas caixas onde o mascaramento simples falhou ou apresentou alta variação de borda com espessura pequena, preservando contornos e evitando modificar o balão inteiro indiscriminadamente.
  - `pcleaner/image_export.py`: exportação em PNG e camadas PSD (`psd-tools`).
- **Compatibilidade (Windows/Linux):** Suporte explícito e scripts dedicados para Windows, Linux (incluindo Flatpak) e macOS.
- **Limitações Conhecidas:**
  - Focado em limpeza de texto; não realiza análise de painéis, associação linguística, tradução nem tipografia/renderização.
  - Licença GPL-3.0-or-later.
- **Estratégia para o MVTE:** **Referência principal para o subsistema de Text Cleaning & Inpainting.** Reaproveitar os padrões técnicos (ajuste de máscara por uniformidade de borda, inpainting seletivo com LaMa apenas quando necessário, separação estrita entre núcleo CLI/engine e GUI, e exportação em camadas).

---

### 1.4. Manga Translation Pipeline
- **URL informada:** `https://github.com/ArsVie/Manga-Translation-Pipeline`
- **Status observado:** **Repositório não encontrado (`Repository not found` / 404)** no GitHub no momento da verificação (`git clone` e `git ls-remote`). Pesquisas complementares indicam atividade do autor `ArsVie` no Hugging Face (`ArsVie/manga_translation_pipeline`), porém sem código-fonte GitHub acessível para auditoria direta.
- **Estratégia para o MVTE:** Conforme as regras de engenharia do projeto, **não presumir nem inventar funcionalidades** não verificadas diretamente no código. Considerado indisponível para reutilização direta.

---

### 1.5. mnga-tr
- **URL:** `https://github.com/mugenyume/mnga-tr` (espelho/fork de `ogkalu2/comic-translate`)
- **Último commit observado:** `2024-12-05` (`Update requirements.txt`)
- **Licença:** **Apache-2.0** (permissiva).
- **Linguagem e Frameworks:** Python `>=3.10`, `PySide6>=6.7.2`, OpenCV, PyTorch `>=2.1.0`, `ultralytics<=8.3.40`, `largestinteriorrectangle>=0.2.0`, `manga_ocr`, `pororo`, `easyocr`, `paddleocr`, `paddlepaddle`, `transformers`, além de SDKs em nuvem (`openai`, `google-generativeai`, `anthropic`, `deepl`, `azure-ai-vision-imageanalysis`).
- **Arquitetura Interna:**
  - `pipeline.py` (`ComicTranslatePipeline`): orquestrador acoplado diretamente à interface Qt (`main_page`, `MoveableRectItem`).
  - `modules/detection.py` (`TextBlockDetector`): executa 3 modelos YOLO (`comic-speech-bubble-detector.pt`, `comic-text-segmenter.pt`, `manga-text-detector.pt`) e usa `largestinteriorrectangle` para calcular áreas internas de limpeza/renderização.
  - `modules/ocr/ocr.py` (`OCRProcessor`): roteia entre backends locais (`manga_ocr`, `pororo`, `easyocr`, `paddleocr`) e nuvem.
  - `modules/translator.py` (`Translator`): focado em APIs em nuvem (GPT-4o, Claude, Gemini, DeepL, Google Translate); não possui motor neural local nem gestão de macro/mesocontexto.
  - `modules/rendering/render.py` e `hyphen_textwrap.py`: quebra de linha com hifenização e ajuste iterativo de tamanho de fonte (`pil_word_wrap`) usando Pillow + `QFontMetrics`.
- **Limitações Conhecidas:**
  - Acoplamento forte entre pipeline e GUI (`PySide6`).
  - Dependência central de APIs em nuvem para tradução de qualidade (viola o princípio de execução exclusivamente local do MVTE).
  - Mistura dependências pesadas (`paddlepaddle` + `torch` + `easyocr`) no mesmo `requirements.txt`.
- **Estratégia para o MVTE:** Licença **Apache-2.0** permite reutilização segura de padrões/utilitários após desacoplamento:
  - Reaproveitar conceito de `largestinteriorrectangle` para área útil interna de balões.
  - Adaptar algoritmo de `hyphen_textwrap` + `pil_word_wrap` (removendo dependência de `PySide6`) como linha de base do motor de Tipografia.
  - Descartar acoplamento com GUI e clientes de nuvem obrigatórios.

---

## 2. Matriz Comparativa

| Critério | comic-text-detector | Manga-Segment | PanelCleaner | Manga-Translation-Pipeline | mnga-tr |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Disponibilidade** | GitHub público | GitHub público | GitHub público | **404 / Indisponível** | GitHub público |
| **Licença** | GPL-3.0 | **AGPL-3.0** | GPL-3.0-or-later | N/A | **Apache-2.0** |
| **Manutenção** | Moderada (2024-04) | Ativa (2026-06) | **Muito ativa (2026-07)** | Desconhecida | Moderada (2024-12) |
| **Escopo Principal** | Detecção de texto + máscara + linhas | Segmentação (painel, balão, caixa, texto) | Limpeza de texto + inpainting | Pipeline (não auditável) | Pipeline completo + GUI |
| **Painéis / Ordem de Leitura** | Não | Painéis (sem ordem) | Não | N/A | Heurística simples RTL/LTR |
| **OCR Local** | Não | Não | Auxiliar (filtro) | N/A | Sim (MangaOCR, EasyOCR, Paddle, Pororo) |
| **Tradução Local** | Não | Não | Não | N/A | Não (foco em nuvem) |
| **Inpainting / Limpeza** | Apenas máscara | Não | **Excelente (máscara + LaMa seletivo)** | N/A | Sim (LaMa / AOT) |
| **Tipografia / Renderização** | Script sintético apenas | Não | Não | N/A | Básico (`pil_word_wrap`) |
| **Desacoplamento GUI** | Sim (CLI/lib) | Sim (CLI/API) | **Sim (`setup-cli.cfg`)** | N/A | **Não (acoplado ao Qt)** |
| **Decisão no MVTE** | **Adaptar (ONNX)** | **Não reusar código (AGPL)** | **Referência principal de limpeza** | **Descartado** | **Reusar padrões Apache-2.0** |

---

## 3. Resumo de Decisões de Reutilização

1. **Reutilizável (conceitos/algoritmos sob Apache-2.0 ou implementação limpa):**
   - Ajuste de fonte com quebra hifenizada e cálculo de retângulo interno útil (`largestinteriorrectangle` / `hyphen_textwrap` de `mnga-tr`).
   - Estratégia de mascaramento por uniformidade de borda e inpainting seletivo (inspirada no `PanelCleaner`, implementada de forma limpa e modular).
2. **Adaptável via Contratos/Interfaces (sem acoplamento direto):**
   - Execução de modelos compatíveis com `comic-text-detector` via **ONNX Runtime** através de adaptador próprio (`VisualDetectionAdapter` / `TextMaskAdapter`).
   - Padronização de saída `SegmentationResult` inspirada na separação de backends, porém escrita do zero sob arquitetura limpa para evitar contaminação AGPL-3.0.
3. **Desenvolver do Zero no MVTE:**
   - **Page Analysis Engine:** detecção global de painéis, divisões visuais e grafo de ordem de leitura.
   - **Text Region Association Engine:** associação geométrica/semântica entre texto, balões, caixas narrativas e texto livre.
   - **OCR & Linguistic Reconstruction Engine:** hierarquia `Page → Panel → Visual Region → Text Block → Sentence → Token`.
   - **Context Management Engine:** Micro, Meso e Macrocontexto com glossário e memória de tradução local (SQLite).
   - **Hybrid Translation Engine:** orquestração 100% local combinando NMT + LLM local (GGUF/ONNX) com revisão contextual.
   - **Typography Analysis & Translation Validation Engine:** correspondência tipográfica local e validação automatizada/manual rastreável.
