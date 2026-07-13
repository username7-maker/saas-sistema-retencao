# Phase 10: Integridade operacional da fila de tasks do piloto - Research

**Researched:** 2026-07-13  
**Domain:** fila operacional multi-origem, deduplicacao, concorrencia e efeitos externos duraveis  
**Confidence:** HIGH para o estado atual do repositorio; MEDIUM para o desenho estrutural que ainda exige migration e teste concorrente em PostgreSQL

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- `Task` permanece o ledger operacional; `WorkQueueItem` continua sendo contrato semantico derivado.
- `/tasks` e `/ai/triage` continuam compartilhando `WorkExecutionView`.
- A experiencia principal continua staff-first, orientada a uma acao clara por vez.
- Efeitos externos permanecem humanos, visiveis e auditaveis.
- Item critico/degradado continua exigindo confirmacao curta.
- A lista completa legada e seus ajustes visuais ficam fora deste corte.

### Prioridade do corte

1. Nenhum trabalho invisivel: alcance, busca e contagem server-side.
2. Nenhum trabalho artificial: reuso e deduplicacao de task ativa.
3. Nenhuma execucao ambigua: frescor, owner, prazo, estado, snooze e ordenacao.
4. Nenhuma colisao silenciosa: claim/versao.
5. Nenhum efeito externo inseguro: consentimento aplicavel e idempotencia persistente.
6. Nenhuma conclusao sem prova: suites focadas e smoke sintetico.

### Contrato de interface

#### Fila

- Busca remota com debounce, estado de carregamento e mensagem de erro recuperavel.
- Navegacao incremental preservando item selecionado quando ele ainda pertence ao resultado.
- Total autoritativo exibido como dado da API, nunca inferido de `items.length`.
- Contadores com skeleton/ellipsis enquanto carregam, sem placeholder numerico enganoso.

#### Item e CTA

- Recomendacao com task ativa: `Continuar tarefa` como CTA principal e link para a task canonica.
- Item snoozed: ausente de `Fazer agora` ate `visible_from`/prazo canonico.
- Dado desconhecido: rotulo `Nao informado` ou `Sem dado`, sem cor critica automatica.
- Recomendacao stale: aviso de atualizacao e CTA seguro para recalcular/atualizar antes de executar quando necessario.
- Item assumido: nome do responsavel e conflito explicito para outro operador.

#### Feedback

- Claim bem-sucedido atualiza a fila e o inspector sem reload integral.
- Conflito 409 preserva contexto, informa que o item mudou e oferece `Atualizar fila`.
- Snooze confirma data/hora de retorno e retira o card imediatamente.
- Repeticao idempotente reapresenta o resultado anterior, sem segundo efeito no provider.

### Compatibilidade e acessibilidade

- Reutilizar componentes/tokens Cordex existentes; nenhuma nova linguagem visual.
- Estados nao podem depender apenas de cor.
- Controles de busca, paginacao, filtros, claim e refresh devem ser acessiveis por teclado e ter nome discernivel.
- Mobile empilha fila e inspector sem esconder acesso a paginacao ou ao estado do claim.

### the agent's Discretion

O `10-CONTEXT.md` nao declara uma secao de discricionariedade adicional.

### Deferred Ideas (OUT OF SCOPE)

- Mudanca visual ampla na lista completa.
- Automacao de envio.
- Novas permissoes.
- Metricas executivas completas.
</user_constraints>

## Post-research scope decision (authoritative)

The transactional review found that the no-migration P0 and provider/concurrency hardening cannot share one validation gate. The roadmap and requirements were therefore split after this research was drafted:

- **Phase 10 now owns:** `WQ-01`, `WQ-02`, sequential reuse from `WQ-03`, `WQ-04`, `WQ-05` and `WQ-08`.
- **Phase 10.1 / Spec 055 owns:** canonical concurrent dedupe, `WQ-06`, `WQ-07` and PostgreSQL/provider proof in `WQ-09`.
- Waves 3A and 3B below remain valid architecture research for Phase 10.1, but the Phase 10 planner must not create their implementation tasks.
- Phase 10 must explicitly avoid claiming concurrency, consent or provider idempotency closure.

<phase_requirements>
## Phase Requirements

| ID | Description | Research support |
|---|---|---|
| WQ-01 | Busca e paginacao server-side alem dos primeiros 25 itens | Envelope proprio, busca no request e paginacao depois de filtros; caps internos sinalizados |
| WQ-02 | Totais e contadores autoritativos, sem zero provisorio | `state_counts` calculado no mesmo snapshot/filtro e estado de loading separado no runner |
| WQ-03 | Reusar task ativa equivalente em preparacoes sequenciais | Reuso sem migration nesta fase; chave canonica concorrente transferida para Phase 10.1 |
| WQ-04 | Expor frescor, owner/equipe, prazo, motivo e `unknown` real | Campos aditivos no contrato; nao reinterpretar `0` legado como ausencia comprovada |
| WQ-05 | Estado, snooze e ordenacao coerentes | Unificar em `visible_from`; corrigir desempate que hoje favorece prazo posterior |
| WQ-08 | Regressao e smoke sintetico nas duas superficies | Suite compartilhada de `WorkExecutionView`, testes backend focados e smoke sem dado real |

Deferred requirements `WQ-06`, `WQ-07` and `WQ-09` are documented for Phase 10.1 / Spec 055, not acceptance criteria for this phase.
</phase_requirements>

## Summary

O menor slice P0 seguro nao precisa de nova dependencia nem migration. Ele pode evoluir o endpoint para um envelope aditivo com `items`, `total`, `page`, `page_size`, `state_counts` e `truncated_sources`; aceitar `q`; aplicar busca/filtros/ordenacao antes do recorte da pagina; unificar snooze em `visible_from`; corrigir o desempate de prazo; e fazer o runner consumir esse contrato com busca remota, loading honesto e navegacao incremental. Esse slice e operacionalmente valioso desde que `total` seja tratado como autoritativo apenas quando `truncated_sources` estiver vazio. Quando houver cap, a API deve declarar limite inferior, nunca exatidao.

O repositorio atual compoe cinco origens em memoria. Antes da composicao, limita `Task` a 300, AI triage a 200, AI Service Agent a 100, Student Personal AI a 100 e assessment queue a 200. Em seguida filtra, ordena, calcula `len(filtered)` e corta a pagina. Por isso a API atual nao consegue provar total global exato, e a busca do frontend enxerga somente os 25 itens recebidos. A resposta correta para o P0 e honestidade explicita sobre truncamento, nao uma falsa promessa de consulta global perfeita.

Reuso de task ativa e exposicao de frescor/prontidao tambem cabem em um slice sem migration, mas isso fecha apenas repeticoes sequenciais. Garantia canonica sob concorrencia, claim/version e efeito externo exatamente-uma-vez exigem persistencia estrutural, constraint unica e teste com transacoes concorrentes. A Wave 3 deve ser planejada separadamente e nao pode ser considerada concluida por mocks unitarios.

**Primary recommendation:** executar 10-01, 10-02 e o runner/gate 10-03 sem migration, com semantica honesta de truncamento; reservar migration e teste PostgreSQL real para unicidade canonica, claim/version e idempotencia de provider na Phase 10.1.

## Project Constraints (from AGENTS.md)

- GSD e o sistema de execucao; Spec Kit e o contrato formal; docs de planning guardam decisoes.
- Nao adicionar Ruflo ao runtime backend/frontend.
- Ler fase GSD e spec antes de editar; manter implementacao local e ownership explicito.
- Nao escrever backend, frontend, planning e docs simultaneamente sem plano de fase.
- Mudancas em auth, tenant, LGPD, Kommo, WhatsApp ou seguranca de IA exigem testes dedicados.
- Depois de cada corte, rodar testes focados e lint/build relevantes.
- Sugestoes geradas por IA permanecem rascunho ate verificacao em codigo, testes e intencao de produto.
- Esta pesquisa nao altera codigo de produto e nao recomenda tocar a lista legada dirty.

## Standard Stack

Nao instalar bibliotecas novas. Usar o stack ja fixado no repositorio.

| Layer | Existing stack | Version in repo | Use in this phase |
|---|---|---:|---|
| API | FastAPI + Pydantic | 0.136.1 / 2.10.6 | request params, envelope e 409 tipado |
| Persistence | SQLAlchemy + PostgreSQL + Alembic | 2.0.38 / driver 2.9.10 / 1.14.1 | consultas tenant-scoped, locks, constraints e migration |
| Backend tests | pytest | 9.0.3 | unitarios, contratos e integracao concorrente |
| UI | React + TypeScript | 18.3.1 / 5.7.3 | runner compartilhado e tipos aditivos |
| Server state | TanStack React Query | ^5.62.7 | cache por filtros/pagina, invalidacao e loading |
| Frontend tests | Vitest + Testing Library | 4.0.18 / 16.3.2 | regressao do runner e wrappers |

**Version note:** versoes foram verificadas nos manifests locais. Nao houve consulta a registry porque nenhuma dependencia nova e recomendada.

## Current Architecture and Evidence

### Read path

1. `routers/work_queue.py` aceita estado, turno, responsavel, dominio, origem, bucket e pagina, mas nao busca.
2. `work_queue_service.py` carrega listas limitadas por origem (`_list_*_items`).
3. `_filter_items()` classifica em Python e `_work_item_score()` ordena.
4. `list_work_queue_items()` calcula `total = len(filtered)` e fatia a pagina.
5. `WorkExecutionView.tsx` fixa `page: 1`, `page_size: 25`, executa queries separadas por tab e faz `filterItems()` local.
6. `/tasks` e `/ai/triage` realmente reutilizam o mesmo `WorkExecutionView`; esse e o seam correto para a regressao cruzada.

### Gaps confirmed in current code

| Finding | Evidence | Consequence | Confidence |
|---|---|---|---|
| Caps precedem filtros | `work_queue_service.py` `_list_task_items` (300), `_list_ai_items` (200), dois Autopilot (100), assessment (200) | `total` pode ser apenas limite inferior | HIGH |
| Busca e somente client-side | `WorkExecutionView.tsx` `filterItems()` sobre `activeQuery.data.items` | item fora dos primeiros 25 e invisivel | HIGH |
| Contador falso durante load | UI usa `data?.total ?? 0`; query de awaiting so habilita ao abrir a tab | `0` aparece antes de existir resposta | HIGH |
| Snooze usa duas chaves | leitura usa `work_queue_visible_from`; outcome grava `work_queue_snoozed_until` e `due_date` | item TODO pode continuar em `do_now` | HIGH |
| Desempate de prazo invertido | sort faz `reverse=True` sobre tupla `(score, due_at)` | em score igual, prazo mais tarde vence | HIGH |
| AI task e idempotente apenas sequencialmente | `_execute_ai_triage` retorna item preparado; `prepare_*` cria sem lock/constraint | duas transacoes podem criar duas tasks | HIGH |
| Score ausente vira zero | onboarding usa `int(member.onboarding_score or 0)`; coluna e non-null default 0 | ausencia e zero real nao sao distinguiveis | HIGH |
| Claim/version nao existe | schemas e mutacoes nao recebem precondicao; updates sao read-modify-write | ultimo commit vence silenciosamente | HIGH |
| Chave de efeito nao e unica | `AutopilotAction.idempotency_key` tem index, sem unique; criacao e check-then-insert | corrida pode duplicar intent/provider | HIGH |
| Intencao nao e duravel antes do provider | `send_and_wait` cria/flush e chama provider; router so commita ao fim | crash apos envio e antes do commit permite retry duplicado | HIGH |
| Consentimento humano e bypassado | safety exige consentimento apenas se `require_auto_send=True`; send-and-wait usa `False` | efeito manual pode chamar provider sem consentimento aplicavel | HIGH |

### Existing patterns to preserve

- Todas as consultas centrais ja incluem `gym_id`; manter `404` para recurso cross-tenant.
- Router e dono do `commit`; services usam `flush=False`/`commit=False` para compor a transacao.
- `AITriageRecommendation` ja possui natural key unica por tenant/dominio/entidade.
- `Task` possui `extra_data`, eventos e audit log; use-os para compatibilidade aditiva, nao como substituto de constraint concorrente.
- `AutopilotEvent` ja possui unique `(gym_id, deduplication_key)`; reutilizar o padrao de constraint, nao apenas a consulta otimista.
- `core_async_job_service.py` ja demonstra `with_for_update(skip_locked=True)` para claim de worker; e referencia local para semantica de lock, nao para copiar `skip_locked` no claim humano.

## Recommended Contracts

### P0 list response (no migration)

Criar schema especifico para Work Queue; nao ampliar o `PaginatedResponse` generico usado pelo resto da API.

```python
class WorkQueueListOut(BaseModel):
    items: list[WorkQueueItemOut]
    total: int
    page: int
    page_size: int
    state_counts: dict[WorkQueueState, int]
    truncated_sources: list[WorkQueueSourceType]
```

Semantica obrigatoria:

- `q` e normalizado (`strip`, case-insensitive) e aplicado antes da pagina.
- `state_counts` usa turno, assignee, dominio, origem, bucket e busca; ignora apenas o tab `state`.
- `total` e exato somente quando `truncated_sources == []`.
- Quando truncado, UI escreve `Pelo menos N`/`resultado parcial`; nao chama de total exato.
- Buscar `limit + 1` em cada origem permite detectar o cap e retornar no maximo o limite atual.
- Ordenacao final e deterministica: score desc, `due_at` asc com nulos por ultimo, depois `source_type` e `source_id` asc.

### P0 readiness fields (no migration)

Adicionar campos opcionais ao `WorkQueueItemOut` e ao tipo TS:

- `last_refreshed_at`
- `freshness_state`: `fresh | stale | unknown`
- `readiness_missing_fields: string[]`
- `assigned_to_name` e `assigned_to_role` quando resolviveis
- `canonical_task_id` quando uma recommendation reutiliza task ativa

Nao inventar frescor para `Task`: use `updated_at` como timestamp de origem e marque politica/limiar explicitamente. Para AI triage, use `last_refreshed_at`. Nao tratar `onboarding_score == 0` como `unknown`, pois o schema atual nao distingue zero legitimo do default; marque a proveniencia como ambigua e planeje correcao de dados separada se a distincao for requisito de gate.

## Smallest P0 Without Migration

O seguinte corte e implementavel sem mudar banco e deve ser planejado primeiro:

1. Schema/endpoint especializado, `q`, `state_counts`, `truncated_sources` e ordenacao estavel.
2. Detectar caps com `limit + 1`; manter os caps atuais e tornar a limitacao visivel.
3. Unificar snooze em `work_queue_visible_from`; durante compatibilidade, ler fallback de `work_queue_snoozed_until` e gravar ambos, com `visible_from` canonico.
4. Fazer `WorkExecutionView` enviar `q`, pagina e filtros; debounce; loading/erro por contador; pagina incremental; preservar selecao por `source_type:source_id`.
5. Antes de `create_task` na recommendation, validar `prepared_task_id` e consultar task ativa equivalente por `gym_id + member/lead + dominio/source`, excluindo done, cancelled, deleted e operational archive. Reusar e persistir o link.
6. Expor frescor, owner/prazo ausente e motivo sem bloquear quando a lacuna nao impede a acao segura.

**Limite deliberado:** a consulta de task ativa evita duplicata sequencial e corrige o CTA, mas nao e garantia canonica contra duas transacoes simultaneas ou outro produtor de task. WQ-03 so fecha integralmente com a constraint/lock da Wave estrutural.

## Structural Changes Requiring Migration or Real Concurrency

### Canonical task uniqueness

Adicionar `Task.work_dedupe_key` nullable e um indice unico parcial tenant-scoped para rows ativas. A chave deve ser deterministica e versionada, por exemplo `ai-triage:onboarding:member:{member_id}:v1`. Antes da migration:

1. auditar duplicatas sinteticas/ambiente alvo;
2. nunca apagar historico;
3. escolher a task canonica ativa e arquivar/superseder extras apenas com plano explicito;
4. criar constraint; e
5. tratar `IntegrityError` como reuso da vencedora, nao 500.

Uma unique expression diretamente em JSONB seria mais opaca. A coluna explicita e mais indexavel, testavel e legivel.

### Shared claim/version

Como a fila possui cinco tipos de origem, usar um sidecar de coordenacao `work_queue_claims`, nao um novo ledger `work_items`. Ele guarda apenas identidade do item, claimant e versao:

- unique `(gym_id, source_type, source_id)`;
- `claimed_by_user_id`, `claimed_at`, `released_at`;
- `version` inteiro;
- timestamps e indice por tenant/claimant.

Claim e outcome usam compare-and-swap (`WHERE version = expected_version`) na mesma transacao da mutacao da origem. Zero rows atualizadas vira 409 com snapshot recuperavel do claimant atual. Nao usar apenas check em Python nem somente `updated_at`, pois assessment queue e fontes derivadas nao compartilham uma row uniforme.

### Durable external effects

Adicionar unique parcial `(gym_id, idempotency_key)` para `AutopilotAction` quando a chave nao for nula. A chave deve vir do request/acao canonica, nao de `message[:80]`, pois truncamento pode colidir e alteracao cosmetica pode criar efeito novo.

O fluxo correto e em duas fronteiras:

1. transacao A cria-ou-recupera a intent `prepared/planned` e commita;
2. executor chama provider uma vez para a intent persistida;
3. transacao B persiste `sent/awaiting_outcome/succeeded/failed` e provider reference.

Retry retorna a mesma intent/resultado. A constraint resolve corrida; a consulta previa so melhora o caminho comum. Consentimento deve ser avaliado por `effective_channel + effect_type`, inclusive quando `human_initiated=True`. O provider mock deve permanecer intocado quando o gate bloquear.

## Architecture Patterns

### Pattern 1: Snapshot honesty

Compor fontes heterogeneas e aceitavel para o P0, desde que cada fonte informe truncamento. Nao misturar `len(page.items)`, `total do snapshot` e `total global exato` sob o mesmo label.

### Pattern 2: Read model derived, ledgers preserved

`WorkQueueItem` permanece DTO. Mutacoes continuam delegadas a `Task`, `AITriageRecommendation`, `AutopilotAction` e assessment resolution. Claim sidecar coordena concorrencia, mas nao guarda descricao, prioridade ou outcome de negocio.

### Pattern 3: Additive rollout

Backend deve publicar primeiro campos opcionais/envelope compativel; frontend passa a consumi-los depois. Claim/idempotency novos entram sob contrato aditivo e somente viram obrigatorios apos ambos os lados estarem publicados.

### Anti-patterns to avoid

- Aumentar `page_size` para 188 ou remover caps sem budget de query.
- Calcular contadores com tres chamadas independentes e sem snapshot coerente.
- Buscar apenas nos 25 itens carregados.
- Usar `items.length` como total.
- Fazer `SELECT` de dedupe e depois `INSERT` sem lock/constraint.
- Guardar claim somente em estado React.
- Considerar `flush()` como durabilidade antes do provider.
- Concluir teste de concorrencia com uma unica `Session` ou mocks.
- Reabrir/refatorar a lista legada dirty neste corte.

## Don't Hand-Roll

| Problem | Do not build | Use instead |
|---|---|---|
| Server cache/pagination state | cache manual no componente | TanStack Query com query key incluindo filtros, `q`, pagina e tamanho |
| Validation/envelope | dicts soltos | schemas Pydantic e tipos TS espelhados |
| Concurrency | boolean/check em memoria | constraint PostgreSQL, row lock/CAS e transacao |
| Idempotency | `if existing` sem unique | unique tenant-scoped + create-or-get |
| Consent | heuristica por label de botao | policy central por canal/efeito usando registros de consentimento |
| Audit | log textual isolado | `TaskEvent`, `AuditLog`, `AutopilotEvent` existentes |

## Common Pitfalls

### Contagens incoerentes

Calcular tabs apos aplicar o filtro de estado zera os outros estados. Derivar `state_counts` do conjunto com todos os filtros exceto `state`, no mesmo request.

### Busca que parece remota, mas continua local

Incluir debounce na UI sem incluir `q` na query key e no request apenas mascara o bug. Testar um item posicao 126/188 que nao aparece na pagina 1.

### Snooze com duas fontes de tempo

Enquanto `due_date`, `work_queue_snoozed_until` e `work_queue_visible_from` competirem, o item pode reaparecer cedo. Declarar `visible_from` canonico; `due_at` continua SLA/prazo.

### AI sync desativa alem do cap

`sync_ai_triage_recommendations(limit_per_domain=50)` marca como inativas recommendations nao presentes no snapshot limitado. Nao aumentar a promessa de alcance da fila sem testar essa interacao. O sync deve distinguir `nao visto por cap` de `nao mais elegivel` antes de afirmar completude global.

### Unknown impossivel de recuperar

`onboarding_score` e non-null com default zero. Sem provenance/migration, o sistema nao sabe se zero foi medido ou default. A UI pode ser honesta sobre lacunas conhecidas, mas nao pode reconstruir historia inexistente.

### Retry depois de falha do provider

Permitir reutilizacao somente de status bem-sucedidos e ignorar `failed` pode reenviar uma acao cujo provider respondeu mas cujo processo caiu. Persistir provider request/reference e definir politica explicita de retry.

## Files to Plan Around

### Backend, no-migration slice

- `saas-backend/app/schemas/work_queue.py`
- `saas-backend/app/routers/work_queue.py`
- `saas-backend/app/services/work_queue_service.py`
- `saas-backend/app/services/ai_triage_service.py`
- `saas-backend/tests/test_work_queue_service.py`
- `saas-backend/tests/test_ai_triage_service.py`
- `saas-backend/tests/test_ai_triage_router.py`

### Backend, structural slice

- `saas-backend/app/models/task.py`
- `saas-backend/app/models/ai_triage_recommendation.py`
- `saas-backend/app/models/autopilot.py`
- novo modelo/migration de claim e migration de constraints
- `saas-backend/app/services/autopilot_safety_service.py`
- `saas-backend/app/services/autopilot_action_service.py`
- `saas-backend/tests/test_autopilot_services.py`
- novo teste de integracao concorrente PostgreSQL

### Frontend shared runner

- `saas-frontend/src/services/workQueueService.ts`
- `saas-frontend/src/types/index.ts` (editar cirurgicamente; arquivo possui mudanca local distante)
- `saas-frontend/src/components/workQueue/WorkExecutionView.tsx`
- `saas-frontend/src/test/TasksPage.test.tsx`
- `saas-frontend/src/test/AITriageInboxPage.test.tsx`
- recomendado: `saas-frontend/src/test/WorkExecutionView.test.tsx`

## Recommended Waves

### Wave 0 - Contract tests and baseline freeze

- Registrar baseline: backend focado `48 passed`; `AITriageInboxPage` `9/9`; `TasksPage` `9/12`.
- Classificar as tres falhas de `TasksPage` como preexistentes: uma copy sem acento e dois seletores ambiguos de `Onboarding`.
- Escrever primeiro testes do envelope, busca 188 itens, contagens, truncamento, snooze e tie-break.

### Wave 1 - Reachability and truth, no migration

- `q`, envelope, counts, cap detection, deterministic order e canonical `visible_from`.
- Runner remoto com debounce, pagina/load-more, loading/erro por contador e truncamento explicito.
- Fecha o P0 pratico de WQ-01, WQ-02 e WQ-05, limitado pela semantica declarada de snapshot.

### Wave 2 - Reuse and readiness, no migration

- Reusar `prepared_task_id` valido ou task ativa equivalente.
- CTA `Continuar tarefa`, `canonical_task_id`, frescor e lacunas de readiness.
- Fecha UX e repeticao sequencial de WQ-03/WQ-04; nao declarar garantia concorrente.

### Wave 3A - Phase 10.1 only: Claim/CAS and canonical uniqueness

- `work_dedupe_key` unico para task ativa.
- claim sidecar + version/CAS + 409 auditavel.
- Testes PostgreSQL com duas sessoes independentes para dedupe, claim e outcome.
- Fecha WQ-03 e WQ-06 sem acoplar o risco de provider ao rollout de concorrencia da fila.

### Wave 3B - Phase 10.1 only: Consent and durable effect intent

- idempotency unique para Autopilot e intencao commitada antes do provider.
- policy de consentimento por canal/efeito em fluxo humano e send-and-wait.
- Provider sintetico prova zero chamadas no bloqueio e no maximo uma no retry.
- Fecha WQ-07; nao publicar junto de 3A sem validar separadamente a nova fronteira transacional.

### Wave 4 - Shared runner and pilot gate

- Regressao compartilhada de `WorkExecutionView` nas duas rotas.
- Typecheck, lint focal, build, `specify check` e smoke sintetico separado em backend/frontend/nao verificavel.
- Nenhuma credencial, conta ou dado real do piloto.

## Validation Architecture (Nyquist)

### Current baseline

| Area | Baseline observed | Interpretation |
|---|---:|---|
| Backend: work queue + AI triage + Autopilot | 48 passed | verde no recorte atual, sem novos cenarios de concorrencia |
| Frontend: AI triage | 9/9 | verde |
| Frontend: TasksPage | 9/12 | tres falhas preexistentes, nao usar como regressao atribuida a Phase 10 |

### Requirements to tests

| Req | Automated proof | Target |
|---|---|---|
| WQ-01 | 188 itens; pagina 2; busca por item originalmente >25 | `test_work_queue_service.py` + router contract |
| WQ-02 | counts ignoram tab state, respeitam demais filtros; truncation honest | backend + `WorkExecutionView.test.tsx` |
| WQ-03 | ativa e reutilizada; done/cancelled/deleted/archived/cross-tenant nao; repeticao sequencial converge | AI triage unit |
| WQ-04 | stale/fresh/unknown, owner e prazo ausentes renderizam sem severidade artificial | backend serialization + runner UI |
| WQ-05 | snoozed sai e volta no instante; due asc e chave estavel | clock-controlled backend tests |
| WQ-08 | mesma suite do runner montada sob `/tasks` e `/ai/triage`; smoke sintetico | Vitest + smoke isolado |

`WQ-06`, `WQ-07` and `WQ-09` require the Phase 10.1 PostgreSQL/provider validation contract and are explicit non-claims here.

### Suggested commands

```powershell
# Per backend task commit
py -3.12 -m pytest saas-backend/tests/test_work_queue_service.py saas-backend/tests/test_ai_triage_service.py saas-backend/tests/test_ai_triage_router.py saas-backend/tests/test_autopilot_services.py -q

# Per frontend task commit
npm.cmd test -- --run src/test/WorkExecutionView.test.tsx src/test/AITriageInboxPage.test.tsx src/test/TasksPage.test.tsx

# Per wave merge
py -3.12 -m pytest saas-backend/tests/test_work_queue_service.py saas-backend/tests/test_ai_triage_service.py saas-backend/tests/test_ai_triage_router.py saas-backend/tests/test_autopilot_services.py -q
npm.cmd run build

# Phase gate, from each project directory as applicable
npm.cmd run lint
npm.cmd run build
specify check
```

### Wave 0 gaps

- [ ] Backend request/response contract for `q`, `state_counts` and `truncated_sources`.
- [ ] Backend 188-item reachability and search outside first 25.
- [ ] Backend canonical snooze/tie-break tests.
- [ ] AI task reuse matrix including cross-tenant and archived.
- [ ] Dedicated shared-runner test for debounce, paging, loading counters, truncation and selection preservation.

The PostgreSQL two-session harness and provider fake are Wave 0 requirements of Phase 10.1, not Phase 10.

### Sampling rate

- **Per task commit:** smallest focused file(s), target under 30 seconds.
- **Per wave merge:** all four backend focused files plus shared runner and both page suites.
- **Phase gate:** full relevant backend/frontend suites, typecheck/lint/build, Spec Kit check and synthetic smoke.

## Open Questions for Planning

1. **Claim scope:** se todos os cinco source types precisam claim no primeiro rollout, use sidecar. Se o piloto limitar claim a `task` e `ai_triage`, registrar essa limitacao explicitamente; nao simular cobertura das demais fontes.
2. **Exact totals after caps:** o P0 aceita lower bound sinalizado. Total global exato exige redesenhar cada source query para filtrar/contar no banco ou materializar um read model; isso nao pertence ao menor slice.
3. **Zero versus unknown:** decidir se provenance de onboarding vira campo persistente. Sem isso, historico `0` nao pode ser reclassificado com confianca.
4. **Existing duplicate rows before unique indexes:** executar auditoria read-only e definir supersedencia nao destrutiva antes da migration.

## Sources

### Primary (HIGH confidence)

- `.planning/STATE.md`, `.planning/ROADMAP.md`, `.planning/REQUIREMENTS.md`
- `10-CONTEXT.md`, `10-PRD.md`, `specs/054-work-queue-integrity-p0/spec.md`, `plan.md`
- `AGENTS.md` e `.planning/config.json`
- implementacao e testes listados em `## Files to Plan Around`
- manifests locais `saas-backend/requirements.runtime.txt`, `requirements.txt` e `saas-frontend/package.json`

Nao foi necessaria pesquisa web: o problema e especifico da implementacao local e todas as conclusoes tecnicas acima foram verificadas no repositorio.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - manifests locais fixam as versoes.
- Current architecture/gaps: HIGH - confirmado em services, schemas, models, routers e runner.
- No-migration slice: HIGH - usa apenas contratos e campos existentes/aditivos.
- Migration/concurrency design: MEDIUM - prescritivo e alinhado aos padroes locais, mas precisa ser validado pelo planner contra dados existentes e PostgreSQL real.
- Baseline tests: HIGH - recorte isolado reportado pelo orquestrador nesta rodada.

**Research date:** 2026-07-13  
**Valid until:** 2026-08-12 ou ate mudanca nos arquivos centrais da Work Queue
