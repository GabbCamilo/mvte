# Registro de Terminais (Terminal Registry)

## 1. OpenCode CLI (Verificado Diretamente)

- **Nome:** `opencode`
- **Executável funcional (Windows):** `C:\Users\Gabriel\AppData\Roaming\npm\opencode.cmd`
- **Alerta de PATH (Descoberta):** `C:\Users\Gabriel\.bun\bin\opencode.exe` aparece primeiro no `PATH`, porém falha ao iniciar (`Bun failed to remap this bin...`). O adaptador **DEVE** resolver explicitamente o caminho `npm\opencode.cmd` (ou caminho validado) no Windows.
- **Versão instalada:** `1.19.5`
- **Sistema Operacional:** Windows (compatível também com Linux).
- **Autenticação:** Configurada via `opencode providers` (`auth.json`), com `OpenRouter api` ativo (1 credencial registrada; detalhes sensíveis omitidos).
- **Capacidade Headless:** Sim (`opencode run`, `opencode serve`, `opencode acp`).
- **Formato de saída:** `--format default` ou `--format json` (eventos JSON brutos).
- **Continuidade de sessão:** Sim (`-c / --continue`, `-s / --session <id>`, `--fork`, `opencode session list`, `opencode export <id>`).
- **Flags confirmadas em `opencode run --help` (v1.19.5):**
  - `--format json|default`
  - `-m, --model <provider/model>`
  - `--agent <agent>`
  - `-f, --file <file>`
  - `-s, --session <id>`, `-c, --continue`, `--fork`
  - `--dir <path>`, `--title <title>`, `--attach <url>`, `--port <num>`, `--variant <v>`
  - **Flags proibidas pela política CDO:** `--auto` (auto-aprovação perigosa).
  - **Flags inexistentes na v1.19.5 (não usar):** `--archived`.
- **Modelos disponíveis (amostra verificada via `opencode models`):**
  - Gratuitos (`opencode/*-free`): `opencode/beam-free`, `opencode/big-pickle`, `opencode/deepseek-v4.1-flash-free`, `opencode/mimo-v2.6-flash-free`, `opencode/nemotron-3.5-lightning-free`, `opencode/nemotron-3.5-super-vl-free`, etc.
  - OpenRouter (`openrouter/*`): ampla lista incluindo famílias Claude, GPT, Gemini, Qwen, DeepSeek e Grok.
