# Phase 4: Import mapper e reconciliacao manual - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase melhora o fluxo atual de preview de importacao para permitir mapeamento e reconciliacao manual de colunas antes do commit final, sem reabrir o escopo de importacao inteira nem criar um ETL generico.

O foco vale para o fluxo de membros e para o fluxo de check-ins dentro da tela atual de importacoes.

</domain>

<decisions>
## Implementation Decisions

### Preview-first mapper
- **D-01:** O mapper entra depois do upload e dentro do fluxo de preview atual; nao existe etapa separada antes da validacao inicial.
- **D-02:** Nenhuma escrita em banco pode acontecer durante mapeamento/reconciliacao; toda a iteracao continua sendo preview-only ate a confirmacao final.
- **D-03:** Depois que o operador ajustar mapeamentos, o sistema deve reprocessar o preview com essas escolhas antes de liberar o commit final.

### Mapping model
- **D-04:** O mapeamento e assistido, nao totalmente livre: cada coluna de origem pode ser ligada a um campo canonico suportado pelo import atual ou marcada como ignorada.
- **D-05:** O sistema nao salva templates persistentes de mapeamento nesta fase; as escolhas valem apenas para o arquivo atual em memoria.
- **D-06:** O sistema deve bloquear conflitos de mapeamento obvios, como duas colunas de origem tentando gravar no mesmo campo canonico sem resolucao explicita do operador.

### UX and operator safety
- **D-07:** O operador deve ver amostra de valores da coluna original no mapper para tomar decisao sem sair da tela.
- **D-08:** Colunas ja reconhecidas automaticamente permanecem travadas como default correto; o operador intervem principalmente em colunas nao reconhecidas, ambiguas ou obrigatorias ausentes.
- **D-09:** O botao final de confirmar importacao so fica habilitado quando o preview reconciliado estiver consistente com os campos obrigatorios do tipo de importacao.

### Scope limits
- **D-10:** Esta fase nao adiciona transformacoes arbitrarias, formulas customizadas, persistencia de templates ou fuzzy matching novo; ela so encaixa reconciliacao manual sobre o parser e aliases ja existentes.
- **D-11:** A fase continua usando a distincao atual entre preview e commit; o commit final reaproveita o mesmo payload de arquivo com um bloco adicional de mapeamento aplicado.

### the agent's Discretion
- O planner pode decidir se o payload de mapeamento vai como `FormData` extra ou JSON serializado, desde que preview e commit aceitem o mesmo contrato.
- O planner pode escolher se o mapper sera tabelado, card-based ou misto, desde que mantenha a tela atual de importacao e a leitura rapida para operador nao tecnico.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning and milestone scope
- `.planning/PROJECT.md` - milestone atual, restricoes operacionais e alvo de `v3.2.0`
- `.planning/REQUIREMENTS.md` - requisitos `IMP-01` e `IMP-02`
- `.planning/ROADMAP.md` - goal e dependencia da Fase 4
- `.planning/STATE.md` - fase atual e contexto acumulado

### Frontend import flow
- `saas-frontend/src/pages/imports/ImportsPage.tsx` - tela atual de importacao, preview e confirmacao
- `saas-frontend/src/services/importExportService.ts` - contratos frontend para preview/import de membros e check-ins
- `saas-frontend/src/types/index.ts` - tipos `ImportPreview`, `ImportSummary` e estruturas associadas
- `saas-frontend/src/test/ImportsPage.test.tsx` - cobertura existente do fluxo preview-before-confirm

### Backend import flow
- `saas-backend/app/routers/imports.py` - endpoints atuais de preview e commit
- `saas-backend/app/services/import_service.py` - parser, aliases, preview, import final e onboarding pos-import
- `saas-backend/tests/test_import_service_parsing.py` - comportamento atual de parser, aliases, preview e import

### External specs
- Nenhum spec externo adicional; o comportamento da fase deve seguir os contratos e restricoes capturados acima.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ImportsPage.tsx` ja tem dois cards operacionais separados por tipo de importacao, com preview, warnings, sample rows e confirmacao final.
- `importExportService.ts` ja encapsula preview/import de membros e check-ins; e o ponto natural para evoluir contrato de payload.
- `ImportPreview` e `ImportSummary` ja representam colunas reconhecidas, nao reconhecidas, warnings, sample rows e erros; isso reduz o que precisa nascer do zero.

### Established Patterns
- O frontend usa `react-query` mutations separadas para preview e commit, com invalidador de queries depois do import confirmado.
- O backend usa aliases de colunas normalizados em `import_service.py`, com parser forte para datas, valores, identificadores e preview sample rows.
- O preview atual e deterministico e sem side effects; o commit final e quem aciona escrita e recalculo de risco.

### Integration Points
- O mapper precisa nascer dentro de `ImportsPage.tsx`, sem criar nova rota.
- O backend deve estender `preview_members_csv`, `preview_checkins_csv`, `import_members_csv` e `import_checkins_csv` para aceitar mapeamentos aplicados.
- Testes existentes em frontend e backend sao o lugar natural para expandir cobertura do novo contrato.

</code_context>

<specifics>
## Specific Ideas

- O operador deve reconciliar visualmente apenas o que nao bateu de primeira, em vez de remapear o arquivo inteiro.
- A interface deve mostrar "coluna de origem -> campo canonico" com exemplos de valores reais da planilha.
- O comportamento final precisa continuar claro para academia: validar, revisar impacto, ajustar colunas se necessario, validar de novo, confirmar importacao.

</specifics>

<deferred>
## Deferred Ideas

- Persistencia de templates de mapeamento por academia
- Heuristica/fuzzy matching mais agressiva para colunas inesperadas
- Pipeline de transformacoes customizadas durante importacao
- Bulk update dedicado fora do import continua na Fase 5
- Busca por telefone/CPF continua na Fase 6

</deferred>

---

*Phase: 04-import-mapper-e-reconciliacao-manual*
*Context gathered: 2026-03-24*
