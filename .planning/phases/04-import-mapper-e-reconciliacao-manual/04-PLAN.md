# Phase 4 Plan

## Workstreams

1. Estender o contrato de importacao para aceitar `column_mappings` e `ignored_columns` no preview e no commit.
2. Enriquecer `ImportPreview` com metadados de reconciliacao e bloquear conflitos de mapeamento no backend.
3. Implementar o mapper inline em `ImportsPage`, preservando a pagina atual e exigindo revalidacao antes do commit final.
4. Cobrir membros e check-ins com testes de backend e frontend para preview, reconciliacao e confirmacao.

## Acceptance

- O operador consegue reconciliar colunas nao reconhecidas sem sair da tela atual de importacao.
- Nenhuma reconciliacao escreve no banco antes da confirmacao final.
- Alterar mapeamentos exige novo preview antes de confirmar.
- Preview e commit usam o mesmo contrato de mapeamento.
- Arquivos que ja seguem o template atual continuam funcionando sem regressao.
