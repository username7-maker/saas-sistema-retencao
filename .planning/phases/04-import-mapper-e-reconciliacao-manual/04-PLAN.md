# Phase 4 Plan

## Workstreams

1. Estender schemas e services de importacao com metadados de mapping.
2. Aceitar `column_mapping` nos endpoints multipart de preview e commit.
3. Adicionar editor visual de colunas em `ImportsPage`.
4. Travar a confirmacao ate a revalidacao do mapping alterado.
5. Cobrir o fluxo com testes backend e frontend.

## Acceptance

- Preview retorna colunas detectadas, sugestoes e faltas obrigatorias.
- Importacao aceita mapping manual para headers fora do dicionario padrao.
- UI permite mapear, ignorar coluna, revalidar e confirmar.
- Import nao fica habilitado quando o mapping esta sujo ou incompleto.
