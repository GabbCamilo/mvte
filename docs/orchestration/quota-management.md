# Gestão de Modelos e Quotas (Quota Management)

## 1. Inventário e Monitoramento
O CDO mantém para cada provedor/modelo: disponibilidade, estado de autenticação (sem expor tokens), erros de quota/rate-limit, tempo de execução e histórico de fallback.

## 2. Política de Fallback
Ao detectar erro de quota ou indisponibilidade:
1. Mover tarefas pendentes daquele provedor para `WAITING_QUOTA`.
2. Não iniciar novas execuções no provedor esgotado.
3. Verificar alternativas válidas já configuradas (ex.: alternar entre modelos `opencode/*-free` ou `openrouter/*` compatíveis com a complexidade da tarefa).
4. **Proibido:** substituir silenciosamente um modelo analítico por um modelo desconhecido/inferior em tarefas arquiteturais críticas sem validação ou aprovação.
5. **Proibido:** compartilhar credenciais entre ferramentas por meios não documentados.
