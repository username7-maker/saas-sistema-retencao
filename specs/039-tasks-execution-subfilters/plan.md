# Plan 039 - Tasks Execution Subfilters

## Technical Plan
1. Registrar spec 039 e fase GSD 09.9.
2. Adicionar `execution_bucket` e `execution_bucket_label` ao contrato `WorkQueueItemOut`.
3. Classificar buckets no backend para onboarding, retencao e professor usando dados estruturados ja existentes.
4. Aceitar query param `bucket` em `/api/v1/work-queue/items` e aplicar filtro antes da paginacao.
5. Atualizar `workQueueService` e `WorkExecutionView` para renderizar e enviar o filtro secundario.
6. Adicionar testes focados para o contrato backend e para a UI.
7. Validar com `specify check`, testes focados, lint/build frontend.

## Risk Control
- Manter bucket opcional para nao quebrar clientes antigos.
- Usar `bucket=all` como padrao.
- Nao alterar ordenacao nem permissao dos itens.
- Nao depender de texto livre quando houver metadata estruturada.
