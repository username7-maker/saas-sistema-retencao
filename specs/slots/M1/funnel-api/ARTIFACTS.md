# ARTIFACTS — funnel-api (worker-B)

## Arquivos criados (todos dentro do território)
- `saas-backend/app/schemas/commercial_funnel.py` — FunnelStage, ConversionBreakdown, WeeklyFunnelResponse.
- `saas-backend/app/services/commercial_funnel_service.py` — `get_weekly_funnel` + janela semanal SP + 4 contadores.
- `saas-backend/app/routers/commercial_funnel.py` — `GET /cockpit/weekly-funnel?week_offset=` (roles OWNER/MANAGER/SALESPERSON/RECEPTIONIST).
- `saas-backend/tests/test_commercial_funnel_service.py` — 13 testes.

## Smoke
`py -3.12 -m pytest saas-backend -q` → **1088 passed** (baseline 1075 + 13 novos), 0 falhas.

## Decisões (desvios documentados da DESIGN-SPEC)
1. **`gym_id` explícito** em todas as funções (mesmo padrão adotado pelo cockpit-api /
   ai_triage) — router passa `current_user.gym_id`.
2. `risk_recovered`: 2 queries (ids com green na janela + histórico desses membros) e
   transição avaliada em Python — membro conta 1× (set), transição = registro
   imediatamente anterior era red/yellow.
3. `members_joined` compara `join_date` (Date) com as datas da janela convertidas pra
   America/Sao_Paulo, inclusivo no fim (join_date não tem hora).
4. Semana fechada (offset<0): `week_end` = início da semana seguinte (exclusivo);
   semana corrente: `week_end = now` — coerente com o CONTRACT (min(now, fim da semana)).

## Pendências pro reconciler
1. Registrar `commercial_funnel.router` no padrão dos existentes.
2. Validar com dado real da ProGym se `direction` NULL tratado como outbound não infla
   `contacts` (regra do CONTRACT — se inflar, reabrir slot com refinamento).
