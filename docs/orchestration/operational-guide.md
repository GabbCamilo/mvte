# Guia Operacional do CDO (Operational Guide)

## Fluxo Padrão de Trabalho
1. **Consultar OpenSpec:** Verificar `openspec/specs/` e `openspec/changes/` antes de planejar.
2. **Decompor:** Quebrar a mudança em tarefas pequenas e independentes, definindo `allowed_files`, `verification_commands` e `retry_limit = 2`.
3. **Provisionar Worktree:** Criar branch e worktree isolada para cada tarefa de implementação.
4. **Delegar via Adapter:** Executar `OpenCodeAdapter.execute_task(...)` com `--format json` e argumentos separados.
5. **Validar (QA):** Coletar saída, inspecionar `git diff`, rodar `pytest` e `openspec validate`, e acionar revisão independente quando aplicável.
6. **Aprovar & Consolidar:** Somente após validação completa, atualizar `tasks.md`, consolidar no Git (com gate humano para merges/publicação) e arquivar a mudança OpenSpec.
