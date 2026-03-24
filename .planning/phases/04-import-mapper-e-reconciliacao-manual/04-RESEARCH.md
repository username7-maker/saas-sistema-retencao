# Phase 4: Import mapper e reconciliacao manual - Research

**Researched:** 2026-03-24
**Domain:** importacao CSV/XLSX com preview, reconciliacao manual e commit seguro
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- O mapper entra dentro do fluxo de preview atual, nao em uma tela separada.
- Nenhuma escrita em banco pode acontecer durante mapeamento/reconciliacao.
- Depois do ajuste manual, o preview precisa ser recalculado antes de liberar o commit.
- O mapeamento e assistido: coluna de origem -> campo canonico suportado ou ignorar.
- As escolhas valem so para o arquivo atual; nada de templates persistidos nesta fase.
- O sistema deve bloquear conflitos obvios de mapeamento.
- O operador precisa ver amostra de valores reais por coluna.
- Colunas reconhecidas permanecem como default correto; a intervencao humana deve focar no que nao foi reconhecido.
- Esta fase nao inclui transformacoes arbitrarias nem fuzzy matching novo.

### the agent's Discretion
- Formato exato do payload de mapeamento entre frontend e backend
- Forma visual do mapper dentro do card atual de importacao

### Deferred Ideas (OUT OF SCOPE)
- Templates persistentes de mapeamento
- ETL customizado por coluna
- Bulk update dedicado
- Busca por telefone/CPF

</user_constraints>

<research_summary>
## Summary

O fluxo atual ja tem a separacao operacional correta entre `preview` e `commit`, mas ainda depende 100% de aliases automaticos. A forma mais segura de evoluir a fase e manter esse trilho intacto e inserir uma camada de `column_mappings` reaproveitada tanto no preview quanto no commit.

A melhor abordagem e fazer o backend receber um bloco opcional de mapeamento no multipart das rotas existentes, aplicar esse mapeamento antes da leitura canonica das colunas e devolver um preview enriquecido com metadados de reconciliacao. Isso evita criar novas rotas, reduz risco de regressao e mantem a UX atual da pagina.

**Primary recommendation:** criar um contrato unico de mapeamento (`column_mappings` + `ignored_columns`) usado por preview e commit, enriquecer `ImportPreview` com estado do mapper e renderizar um mapper inline apenas quando o preview indicar colunas nao reconciliadas.
</research_summary>

## Current System Findings

- `ImportsPage.tsx` ja suporta preview-before-confirm em ambos os cards.
- `ImportPreview` ja entrega `recognized_columns`, `unrecognized_columns`, `warnings`, `sample_rows` e `errors`.
- O backend ja normaliza cabecalhos e trabalha com listas de aliases canonicos.
- O frontend ainda nao tem nenhum estado de mapeamento nem payload adicional para reenviar no commit.
- O backend hoje faz commit dentro de `import_members_csv` e `import_checkins_csv`; isso nao bloqueia a fase, mas exige cuidado para nao criar uma falsa etapa "staged" no preview.

## Recommended Contract Shape

### Request
- Continuar usando `multipart/form-data`
- Adicionar campo serializado `column_mappings`
- Adicionar campo serializado `ignored_columns`
- Reutilizar o mesmo contrato em:
  - `/imports/members/preview`
  - `/imports/members`
  - `/imports/checkins/preview`
  - `/imports/checkins`

### Response
- Estender `ImportPreview` com um bloco de reconciliacao:
  - `mapping_required`
  - `required_targets`
  - `resolved_mappings`
  - `conflicting_targets`
  - `source_columns`
- Cada `source_column` deve carregar:
  - nome original
  - status
  - exemplos de valores
  - candidato sugerido quando houver
  - destino aplicado se ja reconciliado

## Recommended Backend Sequence

1. Extrair a leitura bruta de linhas e cabecalhos para uma etapa reutilizavel.
2. Criar uma funcao de aplicacao de mapeamento sobre os headers normalizados.
3. Fazer preview e commit consumirem a mesma etapa de normalizacao+mapeamento.
4. Enriquecer `ImportPreview` com o bloco de reconciliacao.
5. Manter regras atuais de parser, aliases, onboarding e recalc de risco.

## Recommended Frontend Sequence

1. Estender tipos e service layer para receber/enviar mapeamentos.
2. Introduzir estado local de reconciliacao por card (`members` e `checkins`).
3. Renderizar o bloco `Reconciliar colunas` apenas quando o preview exigir.
4. Invalidar o preview confirmado sempre que o operador mudar um mapeamento.
5. Exigir novo preview antes do botao final de confirmar importacao.

## Common Pitfalls

### Pitfall 1: Mapeamento divergente entre preview e commit
- **What goes wrong:** o operador ve um preview reconciliado, mas o commit usa outro contrato ou cai no parser automatico antigo.
- **How to avoid:** preview e commit precisam compartilhar o mesmo payload e a mesma funcao de aplicacao de mapeamento.

### Pitfall 2: Mapper excessivamente ambicioso
- **What goes wrong:** a fase tenta virar um ETL completo com templates, regras e transformacoes.
- **How to avoid:** limitar a fase a reconciliacao de cabecalho e ignorar coluna.

### Pitfall 3: UX sem revalidacao
- **What goes wrong:** o botao de confirmar continua habilitado com preview velho depois que o operador muda o mapeamento.
- **How to avoid:** qualquer mudanca de mapeamento invalida a confirmacao anterior e exige novo preview.

## Test Strategy

- Backend:
  - preview de membros com coluna nao reconhecida + mapeamento manual
  - preview de check-ins com coluna nao reconhecida + mapeamento manual
  - commit respeitando `column_mappings` e `ignored_columns`
  - conflitos de target bloqueando confirmacao
- Frontend:
  - mapper aparece so quando necessario
  - mudar mapeamento invalida preview anterior
  - confirmar importacao usa o mapping atual
  - membros e check-ins continuam funcionando para arquivos ja reconhecidos

## Open Questions

1. Se colunas ja reconhecidas devem ser reatribuiveis ou so exibidas como leitura.
   - Recomendacao: nesta fase, deixa-las majoritariamente travadas e focar no nao reconhecido.
2. Se conflitos de target serao bloqueados no frontend, backend ou ambos.
   - Recomendacao: validar nos dois; UX preventiva no frontend e garantia final no backend.

## Validation Architecture

- Quick backend command: `pytest saas-backend/tests/test_import_service_parsing.py`
- Quick frontend command: `npm.cmd run test -- src/test/ImportsPage.test.tsx`
- Phase sign-off command:
  - `pytest saas-backend/tests/test_import_service_parsing.py`
  - `npm.cmd run test -- src/test/ImportsPage.test.tsx`
  - `npm.cmd run lint`

