# Arquitetura do Sistema de Orquestração (Antigravity CDO)

## 1. Hierarquia de Controle

```text
NÍVEL 1 — HUMAN OWNER
   ▲ (aprova escopo, arquitetura, credenciais, merges, publicação)
   ▼
NÍVEL 2 — ANTIGRAVITY CDO (Chief Development Orchestrator)
   ├── Task Management System (fila, dependências, estados, histórico)
   ├── Concurrency & Worktree Manager (git worktrees isoladas, max 2 paralelos)
   ├── Permission & Quota Manager (menor privilégio, limites de provedor)
   └── Quality Assurance & Independent Review (diff, testes, OpenSpec)
   ▲ (delega tarefas delimitadas, coleta saída não confiável, valida)
   ▼
NÍVEL 3 — SPECIALIZED AGENTS (Architecture, Python, CV, OCR, Translation, Testing, Docs, Review)
   ▲
   ▼
NÍVEL 4 — EXECUTION TERMINALS (TerminalAdapter: OpenCodeAdapter, etc.)
```

## 2. Arquitetura de Adaptadores de Terminal (`TerminalAdapter`)

Todos os terminais externos são encapsulados atrás de uma interface uniforme para evitar acoplamento com o orquestrador:

- `discover() -> TerminalInfo`: localiza binário funcional, versão e SO.
- `capabilities() -> TerminalCapabilities`: flags confirmadas, suporte headless, JSON, sessão.
- `validate_configuration() -> ValidationResult`: verifica executável e estado de autenticação (sem expor segredos).
- `execute_task(task_spec) -> ExecutionHandle`: dispara execução não interativa com argumentos separados.
- `get_status(handle) -> ExecutionStatus`: monitora processo ativo/concluído/timeout.
- `collect_output(handle) -> RawExecutionResult`: coleta stdout/stderr, eventos JSON, código de saída e arquivos alterados.
- `terminate(handle) -> None`: encerra processo travado ou em loop.
- `continue_session(session_id, prompt) -> ExecutionHandle`: retoma sessão quando suportado.

## 3. Regra de Confiança
Toda saída de um `TerminalAdapter` é tratada como **dado não confiável** até passar pelo `Quality Assurance Manager` (inspeção de diff, escopo de arquivos, testes e conformidade OpenSpec).
