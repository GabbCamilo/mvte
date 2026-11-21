# Plano de Testes — Sistema de Orquestração CDO

## 1. Escopo
Validar descoberta de terminais, construção segura de comandos, validação de configuração, registro de tarefas, isolamento de permissões e coleta de resultados sem depender de execução paga ou destrutiva.

## 2. Casos de Teste Planejados
1. **Descoberta (`discover`):** Verifica que `OpenCodeAdapter` localiza o binário funcional (`npm\opencode.cmd` no Windows, ignorando o shim quebrado `.bun\bin\opencode.exe`) e lê a versão `1.19.5`.
2. **Capacidades (`capabilities`):** Confirma suporte a `--format json`, `--model`, `--agent`, `--dir`, `--session` e ausência de flags proibidas (`--auto`) ou inexistentes (`--archived`).
3. **Validação de Configuração (`validate_configuration`):** Verifica executável e provedor autenticado sem expor credenciais em logs/retornos.
4. **Construção de Comando (`build_command`):** Garante lista de argumentos separados (sem shell injection) e bloqueio explícito caso alguma flag proibida seja solicitada.
5. **Gestão de Tarefas:** Valida transições de estado (`PENDING → ASSIGNED → RUNNING → REVIEWING → APPROVED/REWORK/FAILED`), `retry_limit = 2` e bloqueio de `APPROVED` direto sem validação.
6. **Concorrência:** Garante rejeição de tarefas paralelas com interseção em `allowed_files` e limite máximo de 2 execuções simultâneas.
