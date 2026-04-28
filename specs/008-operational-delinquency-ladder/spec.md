# Feature Spec: Operational Delinquency Ladder

## User Story

Como recepcao ou gestao da academia, quero que recebiveis vencidos virem uma fila operacional clara, para saber quem cobrar hoje, qual valor esta em atraso, qual mensagem usar e qual resultado registrar.

## Scope

### Included

- Detect overdue member receivables from `financial_entries`.
- Treat `open` entries past due as operationally overdue.
- Aggregate one open delinquency task per active member.
- Stage delinquency into D+1, D+3, D+7, D+15 and D+30.
- Materialize/update `Task` with finance metadata and suggested message.
- Register ladder evolution and outcomes in `task_events`.
- Expose finance endpoints for summary, items and task materialization.
- Show delinquency items in Work Queue and Tasks execution mode.
- Add a management summary block to the financial dashboard.

### Excluded

- Automatic payment collection.
- PIX/card/link generation by the system.
- Autonomous WhatsApp/Kommo sending.
- Lead delinquency.
- Bank reconciliation.
- Updating financial entries to paid from a task outcome.

## Requirements

### R1 - Source Of Truth

The V1 source is `financial_entries`. Only active members with receivable entries that are `open` or `overdue`, past due and linked to `member_id` enter the ladder.

### R2 - Ladder Stages

The system must classify overdue members by oldest receivable:

- D+1: friendly reminder.
- D+3: WhatsApp regularization.
- D+7: active contact and offer of help.
- D+15: escalate to manager.
- D+30: high financial risk and review permanence/lock/cancellation.

### R3 - Task Materialization

The system must maintain at most one open delinquency task per member. If the stage changes, update the open task and create a `task_event`.

### R4 - Work Queue

Delinquency tasks must appear as domain `finance` in the unified Work Queue, ordered with high/critical items and hidden from trainers.

### R5 - Outcomes

Financial outcomes must be accepted by Work Queue:

- `payment_confirmed`
- `payment_promised`
- `payment_link_sent`
- `charge_disputed`
- `forwarded_to_manager`

They must update task state and write `task_events`.

### R6 - Dashboard

The financial dashboard must show a collapsible/contained delinquency ladder summary with overdue amount, delinquent members, open tasks, recovered amount in 30 days when inferable and stage breakdown.

### R7 - Guardrails

No external message or collection action is sent automatically. Tenant isolation and role access remain mandatory.

## Acceptance Criteria

- A past-due active member receivable creates one delinquency task.
- Running materialization twice does not create duplicate open tasks.
- Multiple overdue receivables for the same member aggregate into one task.
- A stage change updates the task and creates a timeline event.
- Paid/cancelled entries or entries without member do not create tasks.
- `payment_confirmed` concludes the task and records a task event.
- `payment_promised` keeps the task open and reschedules it.
- `charge_disputed` keeps the task open and escalates to manager.
- Trainers cannot access finance items.
- The daily worker job uses a distributed lock.
