# ARTIFACTS — cockpit-api (worker-A)

## Arquivos criados (todos dentro do território)
- `saas-backend/app/schemas/daily_cockpit.py` — 5 schemas Pydantic do CONTRACT.
- `saas-backend/app/services/daily_cockpit_service.py` — `get_daily_cockpit` + 4 helpers.
- `saas-backend/app/routers/daily_cockpit.py` — `GET /cockpit/daily` (roles OWNER/MANAGER/SALESPERSON/RECEPTIONIST).
- `saas-backend/tests/test_daily_cockpit_service.py` — 18 testes.

## Smoke
`py -3.12 -m pytest saas-backend -q` → **1093 passed** (baseline 1075 + 18 novos), 0 falhas.

## Decisões (desvios documentados da DESIGN-SPEC)
1. **`gym_id` explícito:** `get_daily_cockpit(db, *, gym_id)` e router passa
   `current_user.gym_id` — segue o padrão mais novo do repo (`ai_triage.py`), mais
   forte que o scoping só por sessão que o `dashboard_service` usa. Duas camadas de
   proteção de tenant (invariante 1 do EMPRESA.md).
2. Critério "pendente" da Central Cordex confirmado no código:
   `AITriageRecommendation.approval_state == "pending"`.
3. Ordenações feitas em SQL (`case`) pra top-10 correto com listas capadas.
4. Teste "lead WON não aparece" virou asserção sobre `OPEN_LEAD_STAGES` (o filtro é
   SQL-level; suíte usa mocks de sessão, padrão do repo — sem banco real nos testes).

## Pendências pro reconciler
1. Registrar `daily_cockpit.router` no padrão dos routers existentes
   (`app/routers/__init__.py` / `app/main.py`).
2. Depois do registro, conferir `GET /api/cockpit/daily` com backend de verdade
   (integração real é validada no reconcile + HTC).
