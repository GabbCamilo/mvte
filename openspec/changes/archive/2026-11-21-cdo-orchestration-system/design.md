# Design: cdo-orchestration-system

- **Adapter Layer (`tools/orchestration/opencode_adapter.py`):** Encapsula `discover()`, `capabilities()`, `validate_configuration()`, `build_command()`, `execute_task()`, `get_status()`, `collect_output()`, `terminate()` e `continue_session()`.
- **Registries (`docs/orchestration/registries/`):** `executors.json` e `tasks.json` armazenam estado estruturado para futura integração com painel de observabilidade.
- **Isolamento:** Execuções paralelas limitadas a 2 processos simultâneos, cada um em Git Worktree e branch própria, com inspeção obrigatória pelo CDO antes de qualquer merge.
