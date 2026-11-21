# cleaning-rendering Specification

## Purpose
TBD - created by archiving change mvte-phase4-cleaning-rendering. Update Purpose after archive.

## Requirements

### Requirement: Limpeza Seletiva e Inpainting Não Destrutivo (RF-14)
O sistema SHALL remover o texto original preservando o arquivo de origem e distinguindo fundos uniformes de regiões complexas.

#### Scenario: Limpeza seletiva por uniformidade de borda
- **WHEN** uma região com máscara de caracteres é submetida ao subsistema de limpeza
- **THEN** o sistema avalia a uniformidade da borda ao redor dos caracteres, aplica preenchimento limpo em fundos uniformes sem alterar o balão inteiro e aciona inpainting apenas em regiões complexas
- **AND** preserva a imagem original intacta gerando uma imagem limpa separada.

### Requirement: Correspondência Tipográfica Local Honesta (RF-15)
O sistema SHALL identificar fontes locais semelhantes às características visuais originais sem afirmar recuperação exata quando indisponível.

#### Scenario: Seleção de fonte local e alternativas
- **WHEN** o subsistema tipográfico analisa uma região para inserção de texto traduzido
- **THEN** o sistema seleciona uma fonte local compatível com peso/inclinação/estilo disponíveis e lista alternativas locais ranqueadas marcando `is_exact_match = False` quando não há correspondência exata garantida.

### Requirement: Ajuste Tipográfico sem Truncamento (RF-16)
O sistema SHALL ajustar o texto traduzido à área útil da região sem cortar ou ocultar palavras.

#### Scenario: Adaptação progressiva de texto longo
- **WHEN** o texto traduzido excede o espaço inicial na fonte padrão
- **THEN** o sistema ajusta progressivamente tamanho, distribuição de linhas, espaçamento e fonte alternativa para encaixar todo o conteúdo
- **AND** caso não caiba dentro do limite mínimo legível, marca `needs_manual_review = True` sem truncar palavras.

### Requirement: Composição e Exportação Preservando Dimensões (RF-17)
O sistema SHALL compor a página final combinando camadas visuais e preservando as dimensões originais.

#### Scenario: Exportação da página reconstruída
- **WHEN** a composição final é executada a partir da imagem limpa e dos planos tipográficos
- **THEN** o sistema gera a imagem traduzida com as mesmas dimensões (`width x height`) da página original e registra os caminhos das camadas no `PageDocument`.
