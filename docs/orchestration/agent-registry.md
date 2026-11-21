# Registro de Agentes (Agent Registry)

## 1. Agentes Configurados no OpenCode (`opencode agent list`)
- `build` (`primary`): implementação com leitura/edição e execução de comandos no workspace.
- `explore` (`subagent`): exploração e leitura sem alterações destrutivas.
- `compaction` / `summary` / `title` (`primary`): auxiliares internos de sessão.

*Observação de Segurança:* As permissões globais observadas no OpenCode incluem diretórios de skills externas `mam-*`. Em tarefas do MVTE, o CDO deve instruir explicitamente o agente a **não** acoplar o MVTE ao MAM.

## 2. Papéis Especializados (Nível 3 — MVTE)
| Papel | Terminal / Agente | Perfil de Modelo | Escopo Típico |
| :--- | :--- | :--- | :--- |
| **Architecture Research Agent** | Antigravity / OpenCode (`explore`) | Alta capacidade analítica | Pesquisa, ADRs, análise de repositórios |
| **Python Development Agent** | OpenCode (`build`) | Médio/Rápido (`opencode/*-free` ou `openrouter/*`) | Módulos `domain/`, `application/`, `infrastructure/` |
| **Computer Vision / OCR Agent** | OpenCode (`build`) / Antigravity | Especializado em código/ML | `page_analysis`, `visual_detection`, `segmentation`, `ocr` |
| **Translation Engineering Agent** | OpenCode (`build`) | Contextual | `context_management`, `translation` |
| **Testing Agent** | OpenCode (`build`) | Econômico/Rápido | `tests/unit/`, `tests/benchmarks/` |
| **Documentation Agent** | OpenCode (`build`) | Econômico/Rápido | `docs/`, `README.md`, OpenSpec |
| **Code Review Agent** | Agente distinto do executor | Alta capacidade analítica | Auditoria de diff, regressões e conformidade OpenSpec |
