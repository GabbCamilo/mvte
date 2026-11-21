# Comparação de Modelos de IA Locais (MVTE)

Este documento avalia os modelos de IA candidatos para cada subsistema do MVTE, considerando execução **100% local**, compatibilidade com **Windows e Linux**, suporte a **CPU e GPU (NVIDIA e AMD com 4–8 GB de VRAM)**, quantização e licenciamento.

---

## 1. Detecção Visual e Segmentação Estrutural

| Tarefa | Modelo / Família Candidata | Formato / Backend | VRAM Estimada (FP16/ONNX) | Pontos Fortes | Limitações / Riscos |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Painéis e Ordem de Leitura** | YOLO (v8/v11) ou Magi / heurística morfológica híbrida | ONNX Runtime / PyTorch | ~0.5 – 1.5 GB | Rápido, determinístico, exportável para ONNX | Modelos treinados em mangá variam na licença dos pesos |
| **Balões, Caixas Narrativas e SFX** | YOLO-Seg (ex.: YOLOv8s-seg / YOLOv11s-seg) | ONNX Runtime / Ultralytics | ~0.5 – 1.2 GB | Produz bounding boxes + máscaras poligonais em uma passada | Requer cuidado com licença AGPL-3.0 do Ultralytics se distribuído comercialmente; ONNX Runtime evita dependência em inferência |
| **Texto + Máscara Fina de Caracteres** | Comic Text Detector (YOLOv5 + UNet + DBNet) | ONNX (`comictextdetector.onnx`) | ~0.4 – 0.8 GB | Gera simultaneamente blocos, polígonos de linhas e máscara pixel a pixel | Não distingue balão vs narração vs SFX |

**Recomendação:** Executar todos os modelos de visão preferencialmente via **ONNX Runtime** (`onnxruntime-directml` no Windows para AMD/NVIDIA, `onnxruntime-rocm` ou `onnxruntime-gpu`/CPU no Linux), mantendo interface `DetectorBackend` substituível.

---

## 2. OCR Multilíngue e Reconstrução de Texto

| Idioma / Escrita | Modelo Candidato | Backend Local | Tamanho / VRAM | Observações Técnicas |
| :--- | :--- | :--- | :--- | :--- |
| **Japonês (vertical/horizontal)** | `manga-ocr` (ViT + RoBERTa) | PyTorch / ONNX (exportável) | ~400 MB / ~1.0 GB VRAM | Referência para mangá JP; excelente em furigana e fontes estilizadas; licença Apache-2.0 |
| **Chinês / Coreano / Multi** | `PaddleOCR` (PP-OCRv4) / `RapidOCR` (ONNX) | **RapidOCR (ONNX Runtime)** | ~50–150 MB | **Crítico:** `RapidOCR` roda modelos PP-OCR em ONNX sem exigir `paddlepaddle` (evitando conflitos de `protobuf` e instalação pesada no Windows) |
| **Latino (EN, PT, ES, FR, etc.)** | `EasyOCR` / `RapidOCR` / `TrOCR` | ONNX / PyTorch | ~100–500 MB | RapidOCR/EasyOCR cobrem bem texto impresso; TrOCR útil para fontes artísticas |
| **Multimodal VLM (opcional/futuro)** | Qwen2.5-VL-3B / Florence-2 | `llama.cpp` / ONNX / Transformers | ~2.5 – 4.5 GB (Q4) | Útil para casos de baixíssima legibilidade ou SFX integrado, mas pesado para execução contínua em 4–8 GB VRAM |

**Recomendação:** Adotar arquitetura multi-backend por idioma/escrita: `manga-ocr` (ou versão ONNX) para japonês e `RapidOCR` (ONNX) para chinês, coreano e alfabetos latinos, evitando o peso e conflitos do `paddlepaddle`.

---

## 3. Tradução Neural e Contextual (100% Local)

O requisito de **execução exclusivamente local** em máquinas com **16 GB de RAM e 4–8 GB de VRAM** exige modelos compactos, quantizados e com suporte a múltiplos backends (CPU, Vulkan, ROCm, CUDA).

| Abordagem | Modelo Candidato | Runtime | Memória (Q4_K_M / INT8) | Papel na Tradução Híbrida |
| :--- | :--- | :--- | :--- | :--- |
| **NMT Dedicado (rápido, determinístico)** | `NLLB-200-distilled-600M` / `M2M-100` / `OPUS-MT` | `CTranslate2` (INT8/FP16) | ~0.6 – 1.2 GB RAM/VRAM | Tradução base rápida, rascunho inicial, verificação de omissões e fallback em hardware limitado |
| **LLM Local Compacto (contextual)** | `Qwen2.5-7B-Instruct` ou `Gemma-2-9B` ou `Llama-3.1-8B` (GGUF Q4_K_M) | `llama-cpp-python` (Vulkan / CUDA / ROCm / CPU) | ~4.8 – 6.0 GB | Tradução contextual com glossário, desambiguação de diálogos, preservação de estilo e revisão |
| **LLM Ultra-Compacto (4 GB VRAM / CPU)** | `Qwen2.5-3B-Instruct` ou `Phi-3.5-mini` (GGUF Q4_K_M) | `llama-cpp-python` | ~2.2 – 2.8 GB | Ideal para GPUs de 4 GB VRAM (como a GTX 1650 do ambiente atual) ou execução híbrida CPU+GPU |
| **Embeddings para Memória/Glossário** | `bge-m3` ou `all-MiniLM-L6-v2` | ONNX Runtime / `fastembed` | ~100 – 400 MB | Recuperação seletiva de Macro/Mesocontexto (RAG local) |

**Estratégia de Memória (4–8 GB VRAM):**
Os modelos **NÃO devem permanecer todos carregados simultaneamente na VRAM**. O MVTE deve implementar um **Model Lifecycle Manager** com carregamento sob demanda por estágio do pipeline (`Detect/Segment → OCR → Descarrega Visão → Carrega Tradutor → Descarrega Tradutor → Carrega Inpainting`).

---

## 4. Limpeza e Inpainting

| Modelo | Backend | VRAM Estimada | Qualidade / Uso no MVTE |
| :--- | :--- | :--- | :--- |
| **LaMa (Large Mask Inpainting)** | ONNX / PyTorch (`simple_lama_inpainting` / `lama-cleaner`) | ~0.8 – 1.5 GB | Excelente para remoção de texto sobre hachuras, retículas (*screentones*) e ilustrações |
| **OpenCV Telea / Navier-Stokes** | OpenCV (CPU) | ~0 GB (CPU) | Fallback ultrarrápido para fundos uniformes ou pequenos reparos onde IA não é necessária |
| **Preenchimento Sólido com Máscara Ajustada** | Pillow / OpenCV (CPU) | ~0 GB (CPU) | **Caso prioritário (inspirado no PanelCleaner):** dentro de balões uniformes, evita qualquer perda de qualidade por rede neural |
