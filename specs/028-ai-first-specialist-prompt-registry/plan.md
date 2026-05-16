# Plan 028

## Implementation
- Add specialist model config.
- Add prompt registry service.
- Wire prompt metadata into AI outputs.
- Update UI badges/details.
- Add/adjust focused tests.

## Risks
- LLM failures must fall back safely.
- Metadata must not break existing Pydantic schemas.
- Specialist prompts must not alter deterministic operational rules.

## Rollout
- Safe to deploy with existing flags because no new auto-send is introduced.
- Monitor draft quality and fallback usage in pilot.
