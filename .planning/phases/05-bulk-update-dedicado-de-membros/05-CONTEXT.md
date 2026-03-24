# Phase 5: Bulk update dedicado de membros - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Esta fase cria um fluxo dedicado de atualizacao em massa para membros ja existentes, separado da importacao inicial de base.

O foco e permitir manutencao coletiva segura da base operacional com preview, diff e confirmacao, sem criar novos membros e sem transformar a tela em um ETL generico.

</domain>

<decisions>
## Implementation Decisions

### Bulk update surface
- **D-01:** O fluxo nasce dentro do modulo de membros, acionado a partir da propria `MembersPage`, e nao reaproveita a tela de importacao.
- **D-02:** A experiencia deve viver em uma superficie dedicada de trabalho em massa; o padrao recomendado e uma sub-rota do modulo de membros, nao um drawer compacto.

### Input and matching model
- **D-03:** A atualizacao em massa continua baseada em arquivo (`CSV`/`XLSX`), porque esse e o ritual operacional mais proximo do que a equipe ja usa.
- **D-04:** O arquivo deve atualizar apenas membros existentes. Nunca cria, reativa, exclui ou converte registros nesta fase.
- **D-05:** O match deve ser estrito e previsivel, usando identificadores existentes da base atual: `member_id`, `external_id` (matricula) e `email`.
- **D-06:** O sistema nao deve usar nome como chave de bulk update; isso e fragil demais para manutencao coletiva.

### Allowed update scope
- **D-07:** O primeiro recorte de campos permitidos fica limitado a dados operacionais de membro: `full_name`, `email`, `phone`, `plan_name`, `monthly_fee`, `join_date`, `preferred_shift`, `status` e `external_id`.
- **D-08:** `cpf`, `birthdate`, campos tecnicos de avaliacao, campos de auth e `extra_data` arbitrario ficam fora desta fase.

### Preview and safety
- **D-09:** O fluxo obrigatoriamente e `preview -> revisar diff -> confirmar`. Nenhuma escrita acontece antes da confirmacao final.
- **D-10:** O preview deve mostrar diff entre valor atual e valor proposto por linha/campo, nao apenas contagens agregadas.
- **D-11:** O commit final deve ser bloqueado se houver linhas nao resolvidas, match ambiguo ou valor invalido. Esta fase nao faz aplicacao parcial.
- **D-12:** O operador nao edita valores dentro da grade nesta fase; ele corrige o arquivo e revalida quando necessario.

### Side effects
- **D-13:** Atualizacao em massa deve registrar auditoria e invalidar consultas/paineis relacionados a membros.
- **D-14:** O recalc de risco, se necessario, deve acontecer uma vez apos o commit bem-sucedido, nunca por linha.
- **D-15:** Bulk update nao cria onboarding automaticamente; ele corrige base existente, nao simula entrada de membro novo.

### the agent's Discretion
- O planner pode escolher se o diff principal sera tabelado ou em cards agrupados, desde que preserve leitura rapida de "antes -> depois".
- O planner pode decidir se o backend usa novos endpoints em `/members/bulk-update` ou um sub-router equivalente, desde que o fluxo fique claramente separado de importacao inicial.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning and scope
- `.planning/PROJECT.md` - milestone atual, valor central e restricoes operacionais
- `.planning/REQUIREMENTS.md` - requisitos `BULK-01` e `BULK-02`
- `.planning/ROADMAP.md` - goal e dependencia da Fase 5
- `.planning/STATE.md` - fase atual e progresso acumulado

### Existing members flow
- `saas-frontend/src/pages/members/MembersPage.tsx` - listagem atual, filtros e acoes do modulo de membros
- `saas-frontend/src/services/memberService.ts` - contratos frontend atuais de list/create/update/delete
- `saas-backend/app/routers/members.py` - endpoints atuais de CRUD e permissoes
- `saas-backend/app/services/member_service.py` - listagem e atualizacao individual atuais

### Existing preview/confirm patterns
- `saas-frontend/src/pages/imports/ImportsPage.tsx` - referencia de UX operacional com preview/confirm
- `saas-backend/app/routers/imports.py` - referencia de contrato preview/commit
- `saas-backend/app/services/import_service.py` - referencia de parser, preview e resumo de impacto
- `saas-backend/tests/test_import_service_parsing.py` - referencia de cobertura para preview/import seguro

### External specs
- Nenhum spec externo adicional; as decisoes acima e o codigo atual sao a base da fase.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MembersPage.tsx` ja concentra o contexto certo de busca, filtros e governanca do diretorio de membros.
- `ImportsPage.tsx` ja oferece um padrao forte de `preview-before-confirm` que pode ser reaproveitado em linguagem e estrutura.
- `memberService.ts` e o ponto natural para adicionar os contratos de bulk update no frontend.

### Established Patterns
- O frontend usa `react-query` para preview/commit com invalidador de queries apos sucesso.
- O backend de membros separa router e service layer com audit no router e regra de negocio no service.
- A estrategia de produto continua sendo superficie verdadeira e fluxo seguro antes de gravar.

### Integration Points
- A entrada do fluxo deve sair de `MembersPage`.
- O backend precisa ganhar contratos de preview/commit dedicados para bulk update.
- O diff operacional deve conversar com `MemberUpdate`/`MemberOut`, mas com um payload em lote proprio.

</code_context>

<specifics>
## Specific Ideas

- O operador sobe uma planilha corretiva, ve quem sera atualizado e exatamente quais campos vao mudar.
- A experiencia precisa responder a pergunta operacional principal: "essa planilha vai alterar o que, em quem, e com qual risco?"
- O sistema deve deixar muito claro quando o arquivo esta tentando atualizar alguem que nao existe ou quando a chave veio ambigua.

</specifics>

<deferred>
## Deferred Ideas

- Edicao inline da grade de preview
- Aplicacao parcial com exclusao seletiva de linhas
- Templates persistentes de bulk update
- Bulk update por telefone/CPF continua fora ate a Fase 6

</deferred>

---

*Phase: 05-bulk-update-dedicado-de-membros*
*Context gathered: 2026-03-24*
