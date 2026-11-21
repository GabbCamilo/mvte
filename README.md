# MVTE — Manga Vision & Translation Engine

Sistema independente, modular e **100% local** para leitura, interpretação, tradução contextual e reconstrução visual de páginas de mangá e quadrinhos.

## Arquitetura e Fases Concluídas
O desenvolvimento seguiu integralmente o fluxo **OpenSpec** (`Explore → Proposal → Specify → Design → Tasks → Apply → Verify & Archive`), com especificações permanentes em `openspec/specs/`:

- **Fase 0 — Exploração e Fundamentação:** [repository-analysis.md](docs/research/repository-analysis.md), [model-comparison.md](docs/research/model-comparison.md), [technology-assessment.md](docs/research/technology-assessment.md), [initial-architecture.md](docs/architecture/initial-architecture.md)
- **Fase 1 — Leitor Global de Páginas:** [page-reader/spec.md](openspec/specs/page-reader/spec.md) (`page_analysis`, `visual_detection`, `segmentation`, `text_association`, CLI e GUI PySide6)
- **Fase 2 — OCR e Reconstrução Linguística:** [ocr-linguistic/spec.md](openspec/specs/ocr-linguistic/spec.md) (`ocr` com `RapidOcrAdapter` ONNX / `MangaOcrAdapter`, `linguistic_analysis` com hierarquia `Page → Panel → VisualRegion → TextBlock → Sentence → Token`)
- **Fase 3 — Tradução Contextual:** [contextual-translation/spec.md](openspec/specs/contextual-translation/spec.md) (`context_management` Micro/Meso/Macro em SQLite, TM, glossário e `translation` híbrida local)
- **Fase 4 — Limpeza e Reconstrução Visual:** [cleaning-rendering/spec.md](openspec/specs/cleaning-rendering/spec.md) (`text_cleaning` seletiva por uniformidade de borda, `typography` local sem truncamento, `rendering` em camadas)
- **Fase 5 — Validação e Consolidação:** [validation-consolidation/spec.md](openspec/specs/validation-consolidation/spec.md) (`validation`, `BatchRunner` e contrato independente em [mam-integration-contract.md](docs/integrations/mam-integration-contract.md))

## Instalação e Execução Local

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -e ".[onnx,gui,dev]"
```

### Testes Automatizados
```powershell
.\.venv\Scripts\pytest.exe -v
```

### Uso via CLI e GUI
```powershell
.\.venv\Scripts\mvte.exe caminho/para/pagina.png --direction rtl --save-overlay --transcribe
.\.venv\Scripts\mvte-gui.exe
```

## Governança e Independência
Consulte [AGENTS.md](AGENTS.md) e [openspec/config.yaml](openspec/config.yaml). O MVTE não possui acoplamento com o Manga Archive Manager (MAM); toda integração futura ocorre via contratos em [service_contract.py](src/mvte/interfaces/contracts/service_contract.py).
