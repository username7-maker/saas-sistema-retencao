# Technical Plan

## Backend
- Prompt keys: `retention_copy_agent_v1`, `task_copy_agent_v1`, `onboarding_copy_agent_v1`, `finance_copy_agent_v1`, `commercial_copy_agent_v1`.
- Service: `operational_message_ai_service`.
- APIs: `POST /api/v1/work-queue/items/{source_type}/{source_id}/regenerate-message`.
- Payload: `message_source`, `prompt_key`, `model`, `message_fallback_used`, `message_blocked_reasons`.

## Frontend
- Work Queue badges.
- Regenerate action.
- Prompt/model visibility in message panel.

## Safety
- Block sensitive text, VIP, cancelled member, closed lead, opt-out and finance dispute hints.
