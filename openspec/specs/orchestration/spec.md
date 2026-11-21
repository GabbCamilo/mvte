# orchestration Specification

## Purpose
TBD - created by archiving change cdo-orchestration-system. Update Purpose after archive.

## Requirements

### Requirement: Descoberta e Validação de Terminais Executores (CDO-01)
O sistema de orquestração SHALL descobrir executáveis funcionais, versões e capacidades reais antes de delegar tarefas, sem inventar flags nem expor credenciais.

#### Scenario: Descoberta do OpenCode CLI no Windows
- **WHEN** o adaptador executa `discover()` e `validate_configuration()`
- **THEN** o adaptador resolve o executável funcional (`npm\opencode.cmd`), confirma a versão instalada e valida presença de autenticação sem expor tokens.

### Requirement: Delegação Segura e Não Interativa (CDO-02)
O sistema SHALL construir comandos com argumentos separados, bloqueando flags de auto-aprovação perigosas e tratando saídas como dados não confiáveis.

#### Scenario: Bloqueio de flag proibida
- **WHEN** uma construção de comando tenta incluir `--auto` ou `--dangerously-skip-permissions`
- **THEN** o adaptador rejeita a operação com erro estruturado antes de iniciar qualquer processo.

### Requirement: Ciclo de Tarefas, Isolamento e Validação Independente (CDO-03)
O sistema SHALL manter registro centralizado de tarefas com estados controlados, isolamento por worktree e aprovação condicionada à validação independente.

#### Scenario: Código de saída zero não aprova tarefa automaticamente
- **WHEN** um terminal executor retorna código de saída `0`
- **THEN** a tarefa transita para `REVIEWING` e somente alcança `APPROVED` após verificação de diff, escopo de arquivos, testes e requisitos OpenSpec.
