# Plan

## Technical Design

- Reuse the post-assessment technical ladder from `assessment_service`.
- Represent formal and body composition sources through `assessment_source_type`.
- Use `BodyCompositionEvaluation.measured_at` as cycle base; fallback to `evaluation_date` and then `created_at`.
- Use `measured_at + 90 days` when body composition has no explicit next due date.
- Update assessment analytics to compute effective coverage from formal assessment OR body composition.
- Update Work Queue role/domain routing so assessment queue items can be operational or trainer-specific.

## Data Contract

Technical ladder tasks must include:

- `domain=trainer`
- `owner_role=coach`
- `preferred_shift`
- `work_queue_visible_from`
- `technical_ladder_step`
- `assessment_source_type`
- `assessment_sources`

## Rollout

1. Deploy backend and frontend together.
2. Save one bioimpedance locally and verify tasks.
3. Save one bioimpedance with Actuar sync and verify sync path.
4. Confirm professor queue contains technical tasks only.
5. Confirm operation queue contains first assessment scheduling.
