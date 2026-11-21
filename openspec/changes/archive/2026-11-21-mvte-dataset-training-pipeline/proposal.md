# Proposal: mvte-dataset-training-pipeline

## Why
Testes em páginas reais de mangá demonstraram a necessidade de especializar o detector visual do MVTE para onomatopeias/SFX estilizadas, caixas escuras com texto branco e redução de falsos positivos em ilustrações, aproveitando o acervo local de `.cbz`/`.zip` do usuário de forma isolada e sem acoplar o MVTE ao MAM.

## What Changes
- **Ingestão Somente-Leitura (`tools/training/ingest_archives.py`):** Extrai páginas de `.cbz`/`.zip`/imagens de um diretório fonte configurável para `datasets/raw/` com deduplicação por hash e split determinístico `train/val`, sem modificar os arquivos originais.
- **Pré-rotulagem por Comitê (`tools/training/prelabel_dataset.py`):** Gera anotações iniciais no formato YOLO (`labels/*.txt` + `dataset.yaml`) combinando `RtDetrOnnxDetector` e detecção de texto `RapidOCR`, permitindo curadoria humana antes do treino.
- **Treinamento & Exportação ONNX (`tools/training/train_detector.py`):** Executa fine-tuning compatível com 4 GB VRAM (GTX 1650) em ambiente isolado `.venv-train` e exporta o melhor modelo para `models/mvte-custom-detector.onnx`.

## Out-of-Scope
- Acoplamento de código com o repositório MAM ou modificação de arquivos dentro do MAM.
- Versionamento de imagens/pesos pesados no Git (já ignorados no `.gitignore`).
