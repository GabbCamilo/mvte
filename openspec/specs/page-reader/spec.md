# page-reader Specification

## Purpose
TBD - created by archiving change mvte-phase1-page-reader. Update Purpose after archive.

## Requirements

### Requirement: Importação e Preservação da Página Original (RF-01)
O sistema SHALL importar páginas de imagem preservando o documento original sem degradação de qualidade.

#### Scenario: Importação de página válida
- **WHEN** o usuário ou processo importa um arquivo de imagem suportado (PNG, JPG, WEBP, TIFF)
- **THEN** o sistema cria um `PageDocument` com identificador único, dimensões originais preservadas e referência imutável ao arquivo original
- **AND** nenhuma operação subsequente altera o arquivo original no disco.

#### Scenario: Rejeição de arquivo inválido ou corrompido
- **WHEN** o usuário tenta importar um arquivo inexistente, vazio ou em formato não suportado
- **THEN** o sistema rejeita a entrada com erro estruturado e não cria estado parcial persistido.

### Requirement: Análise Global da Página e Painéis (RF-02)
O sistema SHALL analisar a composição global da página para identificar painéis e ordem de leitura.

#### Scenario: Detecção de painéis e ordem de leitura
- **WHEN** uma página contendo múltiplos quadros é submetida ao subsistema de análise global
- **THEN** o sistema identifica os limites da página, os painéis (`Panel`) com suas coordenadas e atribui uma ordem de leitura configurável (RTL para mangá ou LTR para quadrinhos ocidentais).

### Requirement: Detecção Visual de Estruturas (RF-03)
O sistema SHALL localizar estruturas visuais relevantes usando adaptadores de detecção substituíveis.

#### Scenario: Classificação de elementos visuais
- **WHEN** uma página é processada pelo subsistema de detecção visual
- **THEN** o sistema identifica e classifica regiões como `speech_balloon`, `thought_balloon`, `narration_box`, `sfx` ou `free_text`
- **AND** preserva pontuação de confiança e coordenadas de origem para cada detecção.

#### Scenario: Substituição de backend de detecção
- **WHEN** a configuração seleciona outro adaptador de detecção registrado
- **THEN** o sistema executa o pipeline sem alterar os contratos de saída do domínio.

### Requirement: Segmentação Estrutural e de Caracteres (RF-04)
O sistema SHALL segmentar individualmente as estruturas detectadas sem restringir a representação a caixas retangulares.

#### Scenario: Separação entre máscara estrutural e máscara de caracteres
- **WHEN** uma região visual contendo texto é segmentada
- **THEN** o sistema produz bounding box, máscara poligonal e máscara de pixel para a estrutura visual
- **AND** produz separadamente a máscara de caracteres/texto associada à região.

### Requirement: Associação Espacial e Revisão Manual (RF-05)
O sistema SHALL associar regiões de texto às estruturas visuais correspondentes e permitir correção manual rastreável.

#### Scenario: Associação automática texto-estrutura
- **WHEN** regiões textuais e estruturas visuais (balões/caixas/painéis) são detectadas na mesma página
- **THEN** o sistema associa cada região textual à estrutura visual que a contém ou marca como texto livre quando não há balão envolvente.

#### Scenario: Correção manual com rastreabilidade
- **WHEN** o usuário ajusta manualmente os limites, a classe ou a associação de uma região na visualização de revisão
- **THEN** o sistema atualiza o `PageDocument` marcando a região como revisada manualmente (`manual_override`)
- **AND** registra a alteração no histórico de operações permitindo reversão.
