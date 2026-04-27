# Feature Spec: Operational Execution Queue

## User Story

Como recepcao, professor ou gestor, quero abrir uma fila unica de execucao para saber quem atender agora, qual acao fazer, qual mensagem usar e como registrar o resultado sem navegar por varias telas.

## Scope

### Included

- Unified semantic payload for tasks and AI triage.
- Work queue API under `/api/v1/work-queue/items`.
- Default operational queue in `/tasks`.
- Simplified AI Inbox using the same queue UI.
- Shift-first filtering for staff.
- Confirmation for critical/degraded AI items.
- Fast outcomes for closing the loop.

### Excluded

- Autonomous external sending.
- New durable `work_items` table.
- SLA/throughput dashboard.
- AI-generated execution without human action.

## Requirements

### R1 - Unified Item Contract

The system must expose `Task` and `AITriageRecommendation` as `WorkQueueItem` with source type, subject, domain, severity, preferred shift, reason, primary action, suggested message, state, due date, assignment and context path.

### R2 - Operational Filters

The list endpoint must support filters for state, shift, assignee, domain, source and pagination. The default staff filter is `my_shift`.

### R3 - Execute

The execution endpoint must start a task or prepare an AI triage action. Critical/degraded AI items require explicit confirmation before preparation.

### R4 - Outcome

The outcome endpoint must record an operational result and move the underlying source forward without losing auditability.

### R5 - UI

The primary UI must show a short queue, a focused inspector, the suggested message, one primary CTA and quick outcome buttons. Deep analytical details must be collapsed by default.

### R6 - Guardrails

The V1 must not send external messages autonomously. Every external effect remains human-triggered and visible.

## Acceptance Criteria

- `/tasks` opens in execution mode by default.
- `/tasks` still offers the full task list.
- `/ai/triage` uses the same execution concept.
- Normal item execution requires one CTA click.
- Critical AI item requires confirmation.
- Outcome can be registered without a long form.
- Tenant isolation is enforced in all backend operations.
- Trainer can access only relevant technical task work.
