# Implementation Plan: Operational Delinquency Ladder

## Intent

Transform overdue finance entries into an operational routine inside Tasks + Work Queue without adding autonomous collection behavior.

## Design

- Keep `financial_entries` as V1 financial source.
- Add `delinquency_service` as a domain layer between finance and tasks.
- Use existing `Task` + `TaskEvent` models instead of creating a new work item table.
- Extend Work Queue outcomes and domain filtering to support `finance`.
- Keep financial dashboard as management support, while `/tasks` remains the daily execution entry.

## Backend Work

- Add delinquency schemas in `app.schemas.finance`.
- Add `app.services.delinquency_service`.
- Add `/api/v1/finance/delinquency/summary`.
- Add `/api/v1/finance/delinquency/items`.
- Add `/api/v1/finance/delinquency/materialize-tasks`.
- Add `daily_delinquency_ladder_job` with distributed lock.
- Extend Work Queue domain/outcomes.
- Deny finance tasks to `trainer` and non-finance operational roles.

## Frontend Work

- Add finance service methods.
- Add delinquency types.
- Add financial outcome quick actions to `WorkExecutionView`.
- Add "Regua de inadimplencia" block to `FinancialDashboardPage`.

## Validation

- Backend targeted tests for Work Queue financial outcomes.
- Backend service tests for materialization and no duplicate open tasks.
- Frontend production build.
- Confirm no external sending behavior was introduced.

## Risks

- Financial data may be incomplete or manually maintained.
- `payment_confirmed` does not mark financial entries as paid in V1; finance base still needs source-of-truth update.
- One task per member avoids volume explosion but hides installment-level detail unless the operator opens dashboard/details.
