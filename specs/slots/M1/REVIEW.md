# REVIEW — M1 Cockpit Comercial Diário (pós-reconcile, 2026-07-08)

**Integrador/Reviewer:** time a360 (modo automático). **Veredito: ✅ sem Critical — segue pro HTC.**

## Tier 1 — Fidelidade à DESIGN-SPEC ✅
Nomes, schemas, rotas e componentes batem com as specs dos 3 slots. Desvios documentados
nos ARTIFACTS (todos melhoram aderência ao padrão real do repo):
`gym_id` explícito nos services (padrão ai_triage), base path `/api/v1/*` no FE.

## Tier 2 — Arquitetura ✅
Sem vendor/SDK novo; leitura pura de models existentes; sem cache nos endpoints operacionais.

## Tier 3 — Segurança ✅
RBAC nos 2 endpoints (verificado vivo: 401 sem token via TestClient/OpenAPI);
`week_offset` validado (ge=-12, le=0); sem secrets em código.

## Tier 4 — Invariantes EMPRESA.md ✅
gym_id em toda query (explícito + guard de sessão = 2 camadas); payload LGPD-safe
(nome/telefone, padrão RetentionQueueItem); zero migração de schema; nada hard-coded ProGym.

## Tier 5 — Correção & edges ✅
Semana vazia → zeros; listas vazias → empty states; erro com retry no FE; `direction`
NULL tratado como outbound (regra do CONTRACT, monitorar no piloto); datetimes naive
normalizados pra UTC; membro conta 1× no risk_recovered.

## Tier 6 — Integração cruzada ✅
Types TS = espelho literal dos schemas Pydantic; rotas registradas e presentes no
OpenAPI (`/api/v1/cockpit/daily`, `/api/v1/cockpit/weekly-funnel`); smoke integrado
1107 pytest + build front verdes.

## Nits (não bloqueiam)
- Rota `/dashboard/executive` no FE segue restrita a OWNER/MANAGER; endpoints já aceitam
  SALESPERSON/RECEPTIONIST → decisão de CTO no fechamento (ADR se ampliar).
- `leads_won` usa `updated_at` como proxy de conversão (Lead não tem `converted_at`) —
  documentado; candidato a coluna própria no M2.
