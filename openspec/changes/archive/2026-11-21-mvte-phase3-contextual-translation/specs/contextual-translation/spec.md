## ADDED Requirements

### Requirement: Gestão de Contexto em Três Escalas e Recuperação Seletiva (RF-10)
O sistema SHALL gerenciar contexto em Microcontexto, Mesocontexto e Macrocontexto, recuperando seletivamente apenas informações relevantes para a frase atual.

#### Scenario: Montagem de pacote contextual seletivo
- **WHEN** uma frase dentro de um `PageDocument` é preparada para tradução
- **THEN** o sistema agrega Microcontexto (frase e tokens), Mesocontexto (frases vizinhas da mesma página/diálogo) e apenas os termos do Macrocontexto (glossário, personagens e memória de tradução) que possuem relevância com a frase atual.

### Requirement: Glossário e Memória de Tradução Locais (RF-11)
O sistema SHALL manter glossário terminológico e memória de tradução persistidos localmente para garantir consistência entre páginas e capítulos.

#### Scenario: Reutilização de memória de tradução e aplicação de glossário
- **WHEN** uma obra possui termos cadastrados no glossário ou frases idênticas/similares na memória de tradução
- **THEN** o sistema inclui as correspondências relevantes no pacote contextual e prioriza a consistência terminológica na tradução resultante.

### Requirement: Tradução Híbrida Local sem Alucinação (RF-12)
O sistema SHALL executar tradução híbrida exclusivamente local combinando tradução base e refinamento contextual, sem introduzir informações inexistentes no original.

#### Scenario: Tradução híbrida com backends substituíveis
- **WHEN** um `PageDocument` transcrito é submetido ao `TranslatePageUseCase`
- **THEN** o sistema gera tradução base local, realiza desambiguação/revisão contextual com o pacote de contexto e armazena a tradução vinculada à `Sentence` de origem
- **AND** sinaliza revisão caso haja omissão ou divergência severa sem depender de APIs externas em nuvem.

### Requirement: Revisão Rastreável de Traduções (RF-13)
O sistema SHALL permitir revisão manual e automática das traduções mantendo histórico completo de alterações.

#### Scenario: Edição manual e reversão de tradução
- **WHEN** o usuário altera manualmente o texto traduzido de uma sentença
- **THEN** o sistema atualiza a tradução marcando `manual_override = True` e registra `RevisionEntry` permitindo desfazer a alteração.
