# Proposal: cdo-orchestration-system

## Why
Para escalar o desenvolvimento do MVTE com múltiplos agentes e terminais de IA (como o OpenCode CLI) sem perda de qualidade, conflitos de arquivos ou desvios de escopo, é necessário formalizar o sistema de orquestração CDO (Chief Development Orchestrator).

## What Changes
- Documentação completa de governança, políticas e registros em `docs/orchestration/`.
- Especificação OpenSpec para descoberta de terminais, adaptadores (`TerminalAdapter`), registro de tarefas, isolamento por Git Worktree e validação independente (QA).
- Adaptador inicial `OpenCodeAdapter` em `tools/orchestration/opencode_adapter.py` (sem alterar os módulos centrais do MVTE até aprovação).

## Out-of-Scope
- Implementação de servidor MCP completo (documentado como proposta futura em `docs/orchestration/mcp-evolution-proposal.md`).
- Execução automática de delegações sem aprovação do Human Owner.
