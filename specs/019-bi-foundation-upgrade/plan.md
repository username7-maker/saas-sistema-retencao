# Plan 019 - BI Foundation Upgrade

## Backend

- Expandir `app.schemas.dashboard`.
- Expandir `app.services.dashboard_service`.
- Reutilizar `Member`, `Assessment`, `BodyCompositionEvaluation`, `Task` e `AutopilotAction`.
- Manter tenant scope via contexto atual do dashboard.

## Frontend

- Expandir `BIFoundationDashboard` em `src/types`.
- Atualizar `BIFoundationMini`.
- Atualizar card `Base de BI` em Reports.

## Tests

- Atualizar `test_dashboard_service.py`.
- Atualizar `DashboardLovable.test.tsx`.

## Rollout

- Sem migration.
- Backend e frontend devem subir juntos porque o frontend consome novos campos do payload.
- Se o backend antigo estiver no ar, frontend novo pode quebrar por campos obrigatorios. Publicar em conjunto.
