# Feature Spec: Task Execution Maturity

## User Story

Como operador da academia, quero executar uma tarefa, registrar tentativa, adiar corretamente, comentar e fechar com resultado, para que a rotina diaria vire um historico confiavel de acompanhamento.

## Scope

### Included

- Operational task timeline through `task_events`.
- Fast event registration from task detail and work queue.
- Snooze presets for tomorrow, next week and custom date.
- Outcome recording with contact channel.
- Task productivity metrics for management.
- Server-side filters for the task list.

### Excluded

- Automatic WhatsApp, Kommo or external sending.
- Full backfill of old task history.
- Replacing technical `AuditLog`.
- New `work_items` table.

## Requirements

### R1 - Operational Ledger

The system must store task execution history in `task_events` with tenant, task, member, lead, user, event type, outcome, contact channel, note, scheduled date, metadata and timestamp.

### R2 - Compatibility

The task summary in `Task.extra_data` must remain compatible with existing dashboards and work queue behavior, but new operational actions must also write a `task_event`.

### R3 - Snooze

Operators must be able to postpone a task to tomorrow, next week or a custom date. Snooze must update the task due date, return it to todo and create a timeline event.

### R4 - Outcome

Operators must record results such as responded, no response, scheduled assessment, will return, not interested, invalid number, postponed, forwarded and completed.

### R5 - Timeline UI

The task detail must show a visible operational timeline and allow quick comments/contact attempts without a long form.

### R6 - Metrics

Managers and owners must see productivity metrics: open, overdue, due today, completed today, completed in 7 days, on-time rate, owner breakdown, source breakdown and outcome breakdown.

### R7 - Filters

The task API must support filters for search, priority, source, due bucket, unassigned, member, lead, preferred shift, plan and date range.

### R8 - Guardrails

Tenant isolation and role access must be enforced. Trainers can only access task events for tasks in their technical scope.

## Acceptance Criteria

- Creating a task event for another tenant is blocked.
- Work queue execution creates an `execution_started` event.
- Work queue outcome creates an outcome, forwarded or snoozed event.
- Snooze tomorrow, next week and custom update `due_date`.
- `/api/v1/tasks/{task_id}/events` returns a task timeline.
- `/api/v1/tasks/metrics` returns tenant-safe productivity metrics.
- `/tasks` keeps execution mode as primary and shows metrics collapsed for managers/owners.
- Task detail shows old tasks with a clear empty timeline state.
