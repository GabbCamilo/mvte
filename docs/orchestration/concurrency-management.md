# Gestão de Concorrência e Worktrees (Concurrency Management)

## 1. Limite Inicial Conservador
- Máximo de **2 processos de implementação simultâneos**.
- Processos paralelos só podem rodar se não houver dependência entre tarefas nem interseção em `allowed_files`.

## 2. Isolamento com Git Worktrees
- **Proibido** que dois executores editem o mesmo arquivo ou operem diretamente na branch `main`.
- Cada tarefa paralela recebe:
  - Worktree isolada (ex.: `.worktrees/<task_id>`).
  - Branch dedicada (`task/<task_id>`).
  - Escopo explícito de `allowed_files` e `prohibited_files`.
- A integração de volta para a branch de integração/main é coordenada exclusivamente pelo Antigravity CDO após QA e aprovação humana quando aplicável.
