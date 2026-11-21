# Garantia de Qualidade e Revisão Independente (Quality Assurance)

## 1. Protocolo de Validação do Antigravity CDO
Para cada tarefa concluída por um executor:
1. Capturar estado Git anterior (`HEAD` / `git status`).
2. Listar todos os arquivos modificados (`git diff --name-only`).
3. Verificar violações de escopo (`allowed_files` / `prohibited_files`).
4. Inspecionar diffs linha a linha.
5. Executar testes (`pytest -v`), linters (`ruff`), verificação de tipos e build quando aplicável.
6. Validar especificações OpenSpec (`openspec validate`).
7. Atualizar documentação se necessário e emitir relatório objetivo.

## 2. Regras de Ouro
- Testes ignorados (`SKIPPED`) não contam como aprovados.
- Avisos não devem ser mascarados como aprovação.
- Toda entrega crítica deve passar por **Revisão Independente** (revisor distinto do executor) recebendo: requisito, critérios de aceitação, diff, testes executados, resultados e docs relacionados.
- A aprovação final pertence exclusivamente ao **Antigravity CDO** (e ao **Human Owner** nos gates sensíveis).
