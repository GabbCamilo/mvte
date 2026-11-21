# Proposta de Evolução para MCP (Model Context Protocol)

## Decisão Atual (v1)
Para a primeira versão do sistema de orquestração CDO, **não será criado um servidor MCP próprio**, pois a CLI `opencode run --format json` (v1.19.5) já oferece execução headless, saída estruturada em JSON, seleção de modelos/agentes e continuidade de sessão com menor complexidade operacional.

## Critérios para Evolução para MCP / ACP (v2)
A migração ou exposição via MCP (`opencode mcp` / `opencode acp`) será considerada apenas quando houver necessidade comprovada de:
1. Sessões persistentes de longa duração com múltiplos clientes simultâneos.
2. Exposição de ferramentas do Task Manager, Git Worktree Manager e OpenSpec Validator diretamente como *MCP Tools* para agentes externos.
3. Painel de observabilidade em tempo real consumindo eventos via servidor local (`opencode serve` / `opencode attach`).

## Requisitos Futuros de Segurança
- Manter execução estritamente em `127.0.0.1`.
- Preservar política de menor privilégio por ferramenta exposta.
- Exigir aprovação explícita do Human Owner antes de habilitar qualquer servidor persistente.
