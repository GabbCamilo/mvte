# Contrato de Integração Futura com o MAM

O **MVTE** permanece 100% independente do **Manga Archive Manager (MAM)**, sem importar módulos, schemas ou dependências do MAM.

## Princípios do Contrato
1. **Fronteira por DTOs:** Toda comunicação externa utiliza `TranslationJobRequest` e `TranslationJobResponse` em [service_contract.py](../../src/mvte/interfaces/contracts/service_contract.py) (ou execução via CLI/processo isolado).
2. **Compartilhamento de Modelos:** Modelos baixados localmente podem ser compartilhados via variável de ambiente `MVTE_MODELS_DIR` (ou campo `models_dir` na requisição), evitando duplicação em disco.
3. **Preservação do Original:** O MVTE nunca sobrescreve os arquivos de entrada fornecidos pelo chamador; todas as saídas (`document.json`, `masks/`, `outputs/cleaned.png`, `outputs/translated.png`) são gravadas em `workspace_dir`.
4. **Isolamento de Falhas:** Em processamento em lote (`BatchRunner`), falhas em páginas individuais são reportadas por item sem interromper o lote.
