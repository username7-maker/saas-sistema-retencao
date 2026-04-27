# Implementation Plan: Operational Execution Queue

## Architecture

Use an additive service layer, not a new persistence model:

- `Task` remains the source of truth for manual and operational tasks.
- `AITriageRecommendation` remains the source of truth for AI-assisted recommendations.
- `WorkQueueItem` is a semantic read/execute contract.

## Backend

- Add `app/schemas/work_queue.py`.
- Add `app/services/work_queue_service.py`.
- Add `app/routers/work_queue.py`.
- Register router in `app/main.py`.
- Reuse existing AI triage prepare/outcome services.
- Reuse audit service for task execution and outcome.

## Frontend

- Add `workQueueService`.
- Add `WorkExecutionView`.
- Render `WorkExecutionView` as default in `/tasks`.
- Render `WorkExecutionView` in `/ai/triage` with `source=ai_triage`.
- Preserve previous task list as `Lista completa`.

## Testing

- Backend service tests for task execution, outcome and AI confirmation.
- Frontend tests for execution mode, AI Inbox operation and RBAC.
- Build validation.

## Rollout

- Deploy backend + frontend together.
- Validate with pilot staff before treating the feature as complete.
