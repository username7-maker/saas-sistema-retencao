# Implementation Plan: Cordex Method OS V1

## Technical Context

- Backend: FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL, existing tenant guard via `gym_id`.
- Frontend: React/Vite, TanStack Query, Cordex/Lovable shell, existing role access utilities.
- Governance: GSD remains execution state; Spec Kit captures feature scope.

## Implementation

1. Add Method OS SQLAlchemy models, schemas, migration and seed playbooks.
2. Register tenant-scoped models and expose `/api/v1/method-os` router.
3. Implement services for clients, playbooks, people, events, task generation, human actions, outcomes, dashboards, reports and imports.
4. Add deterministic `method_ai_service` with human-review metadata and safe `wa.me` generation.
5. Add frontend service/types and `/method-os` page with compact operational workflow.
6. Add focused backend/frontend tests and run Spec Kit health checks.

## Compatibility

- Keep existing `Gym`, `Member`, `Lead`, `Task` and dashboard flows working.
- Do not rename current tables or routes.
- Additive migration only; seeded playbooks are idempotent.

## Validation

- `specify check`
- `cd saas-backend; pytest tests/test_method_os*.py tests/test_tenant_fk_guards.py`
- `cd saas-backend; alembic upgrade head`
- `cd saas-frontend; npm run test -- MethodOsPage`
- `cd saas-frontend; npm run build`
