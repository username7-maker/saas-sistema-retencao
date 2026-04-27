# Tasks: Operational Execution Queue

## T1 Backend Contract

- [x] Define `WorkQueueItem`.
- [x] Add list/detail/execute/outcome endpoints.
- [x] Normalize `Task`.
- [x] Normalize `AITriageRecommendation`.
- [x] Add shift, state, assignee, domain and source filters.

## T2 Execution Semantics

- [x] Task execute moves `todo` to `doing`.
- [x] Task execution writes audit metadata.
- [x] AI execute uses existing prepare action flow.
- [x] Critical AI item requires confirmation.
- [x] Prepared AI item does not duplicate task.

## T3 Outcome Semantics

- [x] Task outcomes conclude, postpone or forward.
- [x] AI outcomes map to existing positive/neutral/negative flow.
- [x] Outcome note is optional and short.

## T4 Frontend Execution Mode

- [x] Create reusable `WorkExecutionView`.
- [x] Set `/tasks` default to execution mode.
- [x] Keep full task list available.
- [x] Simplify `/ai/triage`.
- [x] Add quick outcome buttons.

## T5 Validation

- [x] Backend unit tests.
- [x] Frontend targeted tests.
- [x] Frontend production build.
- [ ] Pilot validation with 10 real actions.
- [ ] Staff feedback on time-to-action.
