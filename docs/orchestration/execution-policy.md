# Política de Execução e Retry (Execution Policy)

## 1. Execução Não Interativa (OpenCode)
Comando lógico padrão via lista de argumentos (sem concatenação insegura de strings):
```text
[opencode.cmd, "run", "--format", "json", "--dir", <worktree_path>, "--agent", <agent>, "--model", <provider/model>, <prompt>]
```
*Nota:* Flags como `--auto` são bloqueadas. Todo comando registra início, término, exit code, `session_id`, saída JSON e arquivos modificados.

## 2. Ciclo de Vida de Tarefa (`Task Management System`)
Estados válidos: `PENDING`, `BLOCKED`, `ASSIGNED`, `RUNNING`, `WAITING_QUOTA`, `WAITING_APPROVAL`, `REVIEWING`, `REWORK`, `APPROVED`, `REJECTED`, `FAILED`, `CANCELLED`.

Código de saída `0` **não** implica `APPROVED`; a tarefa passa obrigatoriamente por `REVIEWING` (QA + Revisão Independente).

## 3. Retry & Recuperação de Falhas
- Limite inicial: **máximo 2 tentativas** de correção por tarefa (`retry_limit = 2`).
- Classificação obrigatória antes do retry: erro técnico, arquitetural, operacional ou de quota/disponibilidade.
- Nunca iniciar nova instância enquanto a anterior estiver ativa; encerrar processos travados via `terminate()` preservando logs.
- Se falhar após 2 tentativas: marcar como `BLOCKED` ou `FAILED` e escalar ao Human Owner.
