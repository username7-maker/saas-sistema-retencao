# Tasks: AI-First Operating Inbox

**Feature**: [spec.md](./spec.md)  
**Plan**: [plan.md](./plan.md)  
**Phase Anchor**: `4.43 - AI-first fase 1 - Inbox de triagem`  
**Status**: Ready for execution  
**Created**: 2026-04-18

## Execution Waves

### Wave 1 - Recommendation contract and backend aggregation

- [x] T001 Define the canonical `AI Triage Item` schema and response DTOs in the backend.
- [x] T002 Build the recommendation aggregation service over retention and onboarding signals already present in the product.
- [x] T003 Implement deterministic `why now`, `recommended_channel`, `recommended_owner`, `recommended_action`, and `expected_impact` rules.
- [x] T004 Add list/detail endpoints for the operating inbox.
- [x] T005 Add tenant-safe audit records for suggestion lifecycle states.

### Wave 2 - Inbox UI and approval flow

- [x] T006 Create the dedicated `AI Triage Inbox` route and shell in the frontend.
- [x] T007 Build the inbox list and detail surface with explainability, recommendation summary, and degraded/manual states.
- [x] T008 Add approve/reject interactions item by item.
- [x] T009 Connect approved actions only to the safe tool layer contract:
  - create task
  - assign owner
  - open follow-up
  - prepare outbound message
  - enqueue approved job

### Wave 3 - Outcome measurement and validation

- [x] T010 Persist execution and observed outcome state transitions.
- [x] T011 Instrument metrics required by the `4.43` baseline comparison.
- [x] T012 Add backend tests for payloads, tenant isolation, approval-state transitions, and degraded states.
- [x] T013 Add frontend tests for load/empty/error states, explanation rendering, and approval flows.
- [x] T014 Produce pilot evidence for the first real walkthrough of the inbox and compare it against the frozen manual baseline.

## Notes

- This task list remains intentionally narrow.
- Student coach, AI-generated training, nutrition, wearables, and broad marketing automation remain out of scope.
- Human approval remains mandatory item by item throughout this phase.
