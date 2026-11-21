# AGENTS.md — Instruções Permanentes para Agentes (MVTE)

## 1. Identidade do Projeto
O **Manga Vision & Translation Engine (MVTE)** é um sistema independente, modular e exclusivamente local para leitura, interpretação, tradução contextual e reconstrução visual de páginas de mangá e quadrinhos.

## 2. Regras Obrigatórias
1. **Independência do MAM:** O MVTE NÃO deve possuir acoplamento com o Manga Archive Manager (MAM). Toda futura integração ocorrerá via contratos de entrada/saída bem definidos em `interfaces/`.
2. **Execução Local:** Não introduzir dependências obrigatórias de APIs em nuvem. Modelos de IA devem rodar localmente (CPU ou GPU via adaptadores).
3. **Multiplataforma:** Manter compatibilidade com Windows e Linux (inclusive GPUs NVIDIA, AMD via DirectML/ROCm/Vulkan e execução em CPU).
4. **Governança OpenSpec:** Seguir estritamente o fluxo `Explore → Proposal → Specify → Design → Tasks → Apply → Verify & Archive`.
   - Não implementar código fora de uma mudança OpenSpec com especificação aprovada.
   - Especificações em `openspec/specs/` e `openspec/changes/<change>/specs/` devem usar cenários verificáveis no formato `WHEN / THEN`.
   - Separar requisitos funcionais de decisões tecnológicas.
   - Registrar ADRs apenas após consolidação arquitetural.
5. **Qualidade e Rastreabilidade:**
   - Preservar sempre o documento/imagem original sem perda desnecessária.
   - Manter histórico rastreável de operações e alterações.
   - Não copiar repositórios inteiros indiscriminadamente; respeitar licenças (evitar contaminação por AGPL-3.0; isolar ou substituir componentes GPL-3.0 quando necessário).
   - Todo módulo implementado deve possuir testes automatizados com dados reais licenciados e critérios de aceitação claros.
