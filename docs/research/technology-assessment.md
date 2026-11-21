# Avaliação Tecnológica e de Infraestrutura (MVTE)

Este documento avalia a stack tecnológica selecionada para o MVTE, considerando compatibilidade com **Windows e Linux**, execução **100% local**, restrições de **hardware de referência** e **licenciamento**.

---

## 1. Perfil de Hardware e Implicações Arquiteturais

- **Hardware de Referência do Projeto:** CPU equivalente a Intel Core i7-6700K, 16 GB RAM, GPU AMD Radeon RX 7600 (8 GB VRAM).
- **Ambiente de Desenvolvimento Observado:** Intel Core i5-11400F (6 núcleos), 15.86 GB RAM, NVIDIA GeForce GTX 1650 (4 GB VRAM), Windows, Python 3.11.9, OpenSpec CLI 2.0.0.
- **Implicações Diretas:**
  1. **Suporte Multi-GPU Obrigatório (não depender só de CUDA):** A GPU de referência é **AMD Radeon RX 7600**. No Windows, o ecossistema CUDA não funciona em placas AMD; portanto, o MVTE deve priorizar **ONNX Runtime** (`onnxruntime-directml` no Windows; `onnxruntime` / `rocm` no Linux) para visão computacional e **`llama.cpp` (Vulkan / ROCm / CPU)** para LLMs locais, mantendo adaptadores PyTorch opcionais para CUDA/CPU.
  2. **Orçamento Estrito de VRAM (4–8 GB):** Carregamento sequencial com descarregamento explícito (`unload()` + `gc.collect()`) entre estágios de Visão, OCR, Tradução e Inpainting.

---

## 2. Seleção de Tecnologias por Camada

| Camada / Responsabilidade | Tecnologia Selecionada | Alternativa Avaliada | Justificativa Técnica e de Licença |
| :--- | :--- | :--- | :--- |
| **Linguagem Principal** | Python `>=3.11` | Rust / C++ | Ecossistema nativo de IA/OCR/OpenCV; compatível com Windows e Linux; Python 3.11 já disponível no ambiente. |
| **Gerenciamento de Pacotes** | `uv` / `pyproject.toml` (PEP 621) | `pip` + `requirements.txt` | Resolução determinística, suporte a grupos opcionais (`cpu`, `cuda`, `directml`, `gui`), sem conflitos globais. |
| **Inferência de Visão** | **ONNX Runtime** (`onnxruntime` / `directml`) + adaptador **PyTorch** opcional | TensorFlow + PyTorch | Evita stack duplo pesado (TF+PyTorch como no `Manga-Segment`); acelera tanto NVIDIA quanto AMD no Windows/Linux. |
| **Processamento de Imagem e Geometria** | `opencv-python`, `Pillow`, `numpy`, `shapely`, `pyclipper`, `largestinteriorrectangle` | `scikit-image` | Padrão consolidado; `shapely` + `pyclipper` permitem operações poligonais exatas (sem depender apenas de retângulos); `largestinteriorrectangle` (MIT) calcula áreas úteis em balões irregulares. |
| **OCR Local** | `manga-ocr` (Apache-2.0) + `rapidocr-onnxruntime` (Apache-2.0) | `paddlepaddle` + `paddleocr` | `rapidocr-onnxruntime` entrega os modelos PP-OCR via ONNX sem as incompatibilidades de `protobuf` do `paddlepaddle` observadas no `Manga-Segment`. |
| **Tradução Neural (NMT)** | `ctranslate2` (MIT) + `sentencepiece` | `transformers` puro | Execução em CPU/GPU com quantização INT8, baixíssimo uso de RAM e latência mínima. |
| **LLM Local Contextual** | `llama-cpp-python` (MIT) com modelos GGUF | `ollama` (serviço externo) / `vllm` (Linux-only) | Embutido no processo (sem exigir daemon externo obrigatório), funciona em Windows e Linux com Vulkan (AMD/NVIDIA), CUDA ou CPU. |
| **Inpainting** | LaMa via ONNX / PyTorch + OpenCV Telea | Stable Diffusion Inpaint | LaMa é leve, determinístico e preserva traços de mangá sem alucinar elementos inexistentes. |
| **Tipografia e Renderização** | `Pillow` + `fontTools` / `skia-python` (ou `harfbuzz`/`freetype-py`), `pyphen` (hifenização) | `PySide6` (`QFontMetrics`) acoplado | Desacopla a renderização da GUI! Permite execução headless em CLI, lotes e futura integração com o MAM. |
| **Persistência Local** | **SQLite** (`sqlite3` / `SQLAlchemy`) + arquivos estruturados (JSON/PNG/PSD) | PostgreSQL | Zero configuração, portável entre Windows/Linux, ideal para memória de tradução, glossários, histórico e estado de projetos. |
| **Interface Gráfica (GUI)** | **PySide6** (LGPL-3.0) desacoplada via `application/` | Electron / Web UI | Nativa, multiplataforma, excelente para canvas interativo com zoom, camadas de máscara e revisão manual (como comprovado em `PanelCleaner` e `mnga-tr`), isolada na camada de UI. |
| **Testes e Qualidade** | `pytest`, `ruff`, `mypy` | `unittest` | Padrão moderno Python para testes unitários, de contrato e regressão de métricas. |

---

## 3. Análise de Riscos de Dependências e Licenças

1. **Risco de Licença AGPL-3.0 (`Manga-Segment` / `Ultralytics`):**
   - Não incorporar código do `Manga-Segment`.
   - Em inferência, preferir exportar modelos para **ONNX** e executá-los via **ONNX Runtime** (MIT), evitando dependência obrigatória do pacote `ultralytics` em produção caso o projeto adote licença permissiva.
2. **Risco de Conflito `protobuf` (`PaddlePaddle` vs outros pacotes):**
   - Mitigado ao substituir `paddlepaddle` por `rapidocr-onnxruntime`.
3. **Risco de Quebra de Qualidade de Imagem:**
   - Processar internamente sempre em formato sem perda (PNG / NumPy `uint8` RGB/RGBA), preservando o arquivo original intacto em diretório/camada separada.
4. **Risco de Dependência de Fontes do Sistema:**
   - Utilizar descoberta local de fontes (`matplotlib.font_manager` ou `fontTools` + varredura de diretórios do SO) e incluir fallback open-source (ex.: Noto Sans / Anime Ace) documentado, sem afirmar recuperação exata da fonte original.
