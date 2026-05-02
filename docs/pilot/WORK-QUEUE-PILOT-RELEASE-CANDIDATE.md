# Work Queue Pilot Release Candidate

Date: 2026-05-02
Branch inspected: `pilot-safe/p0-blockers-20260424`
Repo inspected: `C:\aigymos\saas-sistema-retencao-github-latest`

## Status

This bundle is ready for controlled pilot validation, not for claiming pilot completion.

Local automated checks pass for the focused Work Queue, Task, shift, automation journey, and frontend surfaces. Operator evidence is still missing and must be collected before the pilot is marked validated.

Paperclip workspace note: the managed checkout for issue `COR-6` is empty, so reconciliation was performed against the local repo above, where the referenced specs and dirty implementation are present.

## Release Candidate Inventory

### Migrations

- `saas-backend/alembic/versions/20260423_0032_add_user_work_shift.py`
  - Adds `users.work_shift` used by `my_shift` filtering and overnight operators.
- `saas-backend/alembic/versions/20260427_0035_add_task_events.py`
  - Adds `task_events` with task/member/lead/user, event type, outcome, contact channel, scheduled time, metadata, and indexes.
- `saas-backend/alembic/versions/20260428_0036_add_automation_journeys.py`
  - Adds automation journey, step, enrollment, and event tables.
  - Current Alembic head verified as `20260428_0036`.

### Backend Routers And Contracts

- `saas-backend/app/routers/work_queue.py`
  - Lists, fetches, executes, and records outcomes for queue items from `task` and `ai_triage` sources.
- `saas-backend/app/routers/tasks.py`
  - Adds task metrics, operational cleanup preview/apply, task event list/create, and audit logging around task changes.
- `saas-backend/app/routers/automation_journeys.py`
  - Adds templates, list/create/update, preview, activate, pause, and enrollment views.
- Existing domain routers updated for preferred shift exposure:
  - `assessments.py`, `dashboards.py`, `members.py`, `users.py`.
- Router registration touched:
  - `saas-backend/app/main.py`
  - `saas-backend/app/routers/__init__.py`

### Backend Services, Jobs, Models, Schemas

- `saas-backend/app/services/work_queue_service.py`
  - Normalizes Task and AI Inbox items into one queue contract.
  - Enforces role access, source filters, state filters, domain filters, assignee filters, and shift filters.
  - Executes Task items by moving `todo` to `doing`, records task events, and writes audit events.
  - Executes AI Inbox items through the existing prepared action flow and avoids duplicate prepared tasks.
  - Applies quick outcomes, snooze presets, contact channel context, forwarding, and final completion.
  - Feeds automation journey progression from Work Queue task outcomes.
- `saas-backend/app/services/task_service.py`
  - Adds operational metrics, server-side filters, role filtering, archived cleanup, and outcome counts.
- `saas-backend/app/services/preferred_shift_service.py`
  - Normalizes preferred shifts and supports overnight.
- `saas-backend/app/services/automation_journey_service.py`
  - Provides journey templates, preview, activation, safe task generation, idempotency, event recording, and outcome progression.
- Background jobs:
  - `saas-backend/app/background_jobs/jobs.py`
  - `saas-backend/app/background_jobs/scheduler.py`
  - Adds daily preferred shift sync and automation journey processing.
- Models/schemas:
  - `automation_journey.py`, `work_queue.py`, `automation.py`, `task.py`, auth/user schema exports, and model registry updates.

### Frontend Routes, Components, Services

- `saas-frontend/src/pages/tasks/TasksPage.tsx`
  - Defaults to execution mode, keeps full task list available, shows productivity metrics, and scopes by logged-in shift.
- `saas-frontend/src/components/workQueue/WorkExecutionView.tsx`
  - Unified Work Queue execution surface for Tasks and AI Inbox.
  - Supports do-now, awaiting-outcome, all-items modes, `my_shift`, manager all-shifts, quick outcomes, snooze, forwarding, and contact-channel actions.
- `saas-frontend/src/pages/automations/AutomationsPage.tsx`
  - Adds the automation journeys tab as the default automation experience.
- `saas-frontend/src/components/automations/AutomationJourneysPanel.tsx`
  - Lists templates and journeys, previews candidate enrollments/tasks, activates/pauses journeys, and shows output metrics.
- Shift and queue support surfaces:
  - `PreferredShiftBadge.tsx`
  - `preferredShift.ts`
  - `workQueueService.ts`
  - `taskService.ts`
  - `automationJourneyService.ts`
  - shared `types/index.ts`
- Pages updated to display/transport preferred shift context:
  - CRM, retention dashboard, members, settings/users, assessment operations.

### Planning And Pilot Artifacts

- Specs:
  - `specs/006-operational-execution-queue`
  - `specs/007-task-execution-maturity`
  - `specs/009-automation-journeys-os`
  - `specs/010-24h-shift-operations`
- Phase artifacts:
  - `.planning/phases/04.43.3-modo-execucao-operacional-unificado`
  - `.planning/phases/04.43.4-maturidade-operacional-de-tasks`
  - `.planning/phases/04.43.6-automation-journeys-os`
  - `.planning/phases/04.43.7-operacao-24h-por-turno-real`
- Pilot operations doc:
  - `docs/pilot/OPERACAO-24H-DIA-1.md`

## Functional Confirmation

- Task execution:
  - Work Queue Task execute moves actionable tasks into execution.
  - Execution writes task event and audit metadata.
  - Outcome records completion, postponement, no-response, payment promise, forwarding, dispute, or domain-specific result.
- AI Inbox execution:
  - AI Inbox items appear in the same queue.
  - Execution uses the existing prepare flow.
  - Critical AI items require confirmation.
  - Awaiting-result items can receive outcomes from the Work Queue.
- Audit trail:
  - Task create/update/delete, task events, Work Queue execution, Work Queue outcomes, and automation journey changes write audit records.
- Quick outcomes:
  - Frontend exposes quick buttons for completed, responded, no response, postponed, payment-specific outcomes, and forwarding.
- Snooze/contact context:
  - Outcome payload supports `snooze_preset`, `scheduled_for`, `contact_channel`, and operator notes.
- Role filtering:
  - Trainers are restricted to trainer-appropriate technical/coach tasks.
  - Finance-sensitive work remains limited to owner/manager/receptionist roles.
  - AI Inbox remains limited to owner/manager/receptionist.
- Shift filtering:
  - `my_shift` is the default queue scope.
  - Owner/manager can switch to all shifts.
  - Non-manager attempts to use all shifts are coerced back to `my_shift`.
  - Overnight is included in backend normalization and frontend labels.
- Automation journey outputs:
  - Journeys are human-approved task generators, not external auto-senders.
  - Activated journeys create auditable tasks with journey metadata.
  - Work Queue outcomes advance enrollments and journey counters.

## Verification Run

Executed on 2026-05-02:

- Backend focused tests:
  - `python -m pytest tests/test_work_queue_service.py tests/test_task_service.py tests/test_preferred_shift_service.py tests/test_automation_journeys.py`
  - Result: 33 passed.
- Migration sanity:
  - `python -m alembic heads`
  - Result: `20260428_0036 (head)`.
- Frontend focused tests:
  - `npm.cmd test -- src/test/TasksPage.test.tsx src/test/AITriageInboxPage.test.tsx src/test/preferredShift.test.ts`
  - Result: 19 passed.
- Frontend production build:
  - `npm.cmd run build`
  - Result: build completed.

Note: `npm test` through PowerShell failed because `npm.ps1` script execution is disabled on this machine. `npm.cmd` was used successfully.

## Deploy Recommendation

Ship this as one controlled pilot deploy window, not as unrelated smaller deploys.

Reason: the frontend Work Queue depends on backend queue/outcome contracts, task events, preferred shift fields, and automation journey endpoints. Splitting the bundle across days increases the chance that operators see execution UI without the audit/outcome backend, or backend journey/task outputs without the intended operator surface.

Recommended sequence inside one window:

1. Take database backup.
2. Deploy backend with migrations through `20260428_0036`.
3. Confirm `alembic heads` has one head and the app boots with the Work Queue and automation journey routers registered.
4. Deploy frontend build from the same bundle.
5. Keep automation journeys inactive until Work Queue smoke checks pass.
6. Run pilot checklist below with real operators.

Acceptable smaller sequence only if the deploy system requires it:

1. Backend plus migrations as a dark launch.
2. Frontend immediately after backend health checks pass.
3. Automation journey activation only after Work Queue smoke checks and manager/trainer visibility checks pass.

Do not deploy frontend first.

## Rollback Notes

- Frontend rollback:
  - Safe to roll back the frontend build if backend remains forward-compatible. Operators lose the unified execution UI but backend tables/endpoints can remain unused.
- Backend binary rollback:
  - Prefer leaving migrations `0035` and `0036` in place if any task events or journey data were written. Older code should ignore unused tables.
- Strict DB rollback:
  - Only use Alembic downgrade before production writes, or after explicitly accepting data loss.
  - Downgrading `20260428_0036` drops journey, step, enrollment, and journey event data.
  - Downgrading `20260427_0035` drops task event audit history.
- Operational rollback:
  - Pause active automation journeys.
  - Disable automation journey processing in scheduler/runtime if needed.
  - Stop pilot operators from using Work Queue execution mode and return to existing task list flow.
  - Preserve audit/task event tables for post-incident review unless there is a hard schema reason to remove them.

## Pilot Validation Checklist

Pilot validation is not complete until the evidence fields are filled with real operator data.

Capture for every action:

- Operator name and role.
- Shift.
- Source type (`task` or `ai_triage`).
- Source id.
- Start timestamp when the operator opens the item.
- Outcome timestamp.
- Outcome selected.
- Audit or task event evidence.
- Notes on confusion, extra clicks, or missing context.

Required real actions:

1. Receptionist, morning shift, Task source: execute one retention/onboarding task and record `completed` with WhatsApp contact context.
2. Receptionist, morning shift, AI Inbox source: execute one normal AI Inbox item and record a non-pending outcome.
3. Receptionist or manager, awaiting-outcome view: reopen one prepared item and record final outcome from the Work Queue.
4. Trainer, own shift: verify only trainer-appropriate tasks are visible, execute one coach/assessment task, and record outcome.
5. Trainer negative check: confirm finance/commercial AI Inbox work is not visible to the trainer account.
6. Manager all-shifts view: switch from `my_shift` to all shifts and verify morning, afternoon, evening, overnight, and unassigned buckets/counts are inspectable.
7. Overnight operator: execute one non-invasive overnight-safe action and record the outcome without call/collection behavior.
8. Snooze path: record `no_response` or `postponed` with tomorrow or next-week snooze; verify due date and event/audit trail.
9. Forwarding path: forward one task to trainer, reception, or manager; verify it returns to todo state with forwarding metadata and correct visibility.
10. Automation journey output: activate or preview one pilot journey, generate/inspect one resulting task, execute it through Work Queue, and verify journey enrollment/event counters update.

Time-to-action measurement:

- Measure from item open to recorded outcome for all 10 actions.
- Report median and slowest action.
- Record whether the operator opened extra pages to find phone/context.
- Compare against the pre-pilot baseline if one exists; otherwise store this as the baseline for the next pilot window.

Exit criteria:

- All 10 real actions completed by real operators.
- Trainer shift filtering proven with at least one positive and one negative check.
- Manager all-shifts view proven.
- Overnight path proven with non-invasive behavior.
- Time-to-action captured.
- No unresolved audit gaps for executed actions.

## Current Open Item

The implementation can be treated as a release candidate for a controlled pilot, but validation remains pending on operator evidence. The next owner action is to schedule the pilot window and collect the checklist evidence above.
