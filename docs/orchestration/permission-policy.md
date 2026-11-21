# Política de Permissões (Permission Policy)

Princípio fundamental: **Menor Privilégio**.

## 1. Antigravity (Nível 2 — CDO)
- Operar com acesso restrito ao workspace do projeto (`C:\Users\Gabriel\Documents\mvte`).
- Não habilitar acesso global irrestrito nem modificar configurações globais de segurança.
- Exigir aprovação humana para: alterações de escopo/arquitetura, instalação de componentes de sistema, alterações de credenciais, operações destrutivas e publicação/merges definitivos.

## 2. OpenCode CLI e Executores (Nível 3–4)
- **Permitido:** Leitura e inspeção no workspace/worktree designado; edição restrita aos `allowed_files` da tarefa; execução apenas de comandos de teste/validação aprovados (ex.: `pytest`, `ruff`, `openspec validate`).
- **Proibido em qualquer circunstância:**
  - `--auto` (OpenCode)
  - `--dangerously-skip-permissions`
  - `always-proceed` global ou modo Turbo irrestrito
  - Exclusão automática de arquivos fora do escopo
  - Instalação automática de pacotes globais ou alteração de credenciais
  - Push/merge direto na branch `main` por agentes executores
