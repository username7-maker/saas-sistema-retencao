# Tasks: Operational Delinquency Ladder

## Backend

- [x] Add delinquency response schemas.
- [x] Build `delinquency_service` over `financial_entries`.
- [x] Add finance delinquency endpoints.
- [x] Materialize/update one open task per delinquent member.
- [x] Register ladder changes in `task_events`.
- [x] Extend Work Queue with `finance` domain.
- [x] Extend Work Queue outcomes with financial outcomes.
- [x] Add daily worker job with distributed lock.
- [x] Add targeted backend tests.

## Frontend

- [x] Add finance service API methods.
- [x] Add delinquency and financial outcome types.
- [x] Add financial quick outcomes in Work Queue execution inspector.
- [x] Add financial dashboard ladder summary and refresh action.
- [x] Run production build.

## Follow-Up

- [ ] Pilot-test with real overdue entries from ProGym.
- [ ] Decide if `payment_confirmed` should optionally update `financial_entries` in a later phase.
- [ ] Add installment-level drawer if operators need parcel details beyond aggregated task.
