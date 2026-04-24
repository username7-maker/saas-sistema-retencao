# Implementation Plan: AI-First Operating Inbox

**Feature**: [spec.md](./spec.md)  
**Phase Anchor**: `4.43 - AI-first fase 1 - Inbox de triagem`  
**Status**: Ready for execution  
**Created**: 2026-04-16

## Plan Intent

Transform the broad `AI-first OS` concept into the first executable AI-first surface of the AI GYM OS: a unified operating inbox for retention and onboarding that prepares action safely, requires explicit human approval, and produces measurable operational evidence.

This plan is intentionally narrow. It does **not** open a parallel product line for student coach, AI-generated training, nutrition, wearables, or broad marketing automation.

## Gate Status

This plan is now **allowed to enter implementation**.

Satisfied gates:

1. `4.37` closed in `verify/validate`
2. `4.38` closed in `verify/validate`
3. `4.39` closed in `verify/validate`
4. `4.3` passed the monitored pilot gate
5. `4.42.2` to `4.42.5` closed with visual and operational validation in the pilot
6. `4.36+4.40` closed in `verify/validate`
7. `4.32` closed
8. `4.33` closed

## Product Cut

### In scope

- One AI-first inbox for retention and onboarding
- Daily prioritization with explainability
- Recommended next action, owner, channel, message, and expected impact
- Human approval item by item
- Safe tool layer for preparing action
- Audit trail from recommendation to outcome
- Metrics to compare AI-assisted triage against the manual baseline

### Out of scope

- Student-facing AI coach
- AI-generated training plans
- Nutrition and meal tracking
- Wearables / IoT
- Demand-forecast scheduling
- Broad AI marketing suite
- Autonomous execution without approval

## Architecture Direction

### Reuse, do not fork

The implementation should extend the current operational layers already in the product:

- task triage and onboarding context
- member/lead operational context
- existing assistant payload conventions
- durable jobs and audit patterns
- current integrations and fallback states

The inbox is a new top-level operational surface, but it should not introduce a second recommendation stack disconnected from:

- tasks
- onboarding
- retention dashboards
- CRM follow-up context

### Core semantic object

Introduce one shared semantic recommendation model for the inbox:

- item identity
- source domain (`retention`, `onboarding`, or future allowlisted expansion)
- why-now explanation
- recommended owner
- recommended channel
- recommended action
- suggested message
- expected impact
- approval state
- execution state
- outcome state

The UI, auditing, and future reporting should consume this same semantic object instead of each surface inventing its own local interpretation.

### Safe tool layer contract

The tool layer for this phase is constrained to preparing actions already compatible with the current system:

- create task
- assign owner
- open follow-up
- prepare outbound message
- enqueue approved job

No direct send or auto-dispatch belongs in this phase.

## Delivery Slices

### Slice 1 - Semantic recommendation payload

Goal:
- define and serve the inbox item contract from current operational data

Includes:
- normalized recommendation schema
- aggregation from retention + onboarding context
- explanation rules
- safe fallback states when channel or context is degraded

Done when:
- the backend can produce a unified inbox payload without new product modules
- every item explains why it exists now

### Slice 2 - Inbox UI

Goal:
- provide one operating surface for daily triage

Includes:
- inbox list
- detail pane or drawer
- visible explanation of why-now
- recommended action, owner, channel, message, expected impact
- clear empty, degraded, and fallback states

Done when:
- an owner can start the day from this inbox instead of manually stitching dashboards and task queues

### Slice 3 - Approval and action preparation

Goal:
- let operators approve or reject item by item

Includes:
- approve/reject interaction
- safe action preparation only
- audit write for suggestion, decision, prepared action
- no execution outside approved contracts

Done when:
- actions cannot happen without recorded approval

### Slice 4 - Outcome measurement

Goal:
- prove the inbox is improving operations

Includes:
- recommendation acceptance metrics
- triage-time measurement
- action execution counts
- downstream result tracking

Done when:
- the pilot can compare AI-assisted triage against the baseline frozen for `4.43`

## Backend Plan

1. Define the canonical inbox recommendation schema.
2. Build a recommendation aggregation service over existing retention and onboarding signals.
3. Create deterministic explainability rules for `why now`.
4. Add endpoints for:
   - list inbox items
   - get inbox item detail
   - approve/reject recommendation
   - prepare allowed action
5. Persist audit state transitions for suggestion, approval, preparation, execution, and observed outcome.
6. Ensure tenant isolation and durable side-effect rules stay intact.

## Frontend Plan

1. Create a dedicated AI-first inbox route and shell.
2. Build the list + detail layout for daily triage.
3. Reuse existing task/member context where it reduces duplication.
4. Add explicit action approval UI.
5. Add clear degraded/manual states when recommended channels or downstream tools are unavailable.
6. Expose outcome and status traces without turning the inbox into a debug console.

## Data And Observability Plan

The inbox must measure impact using the current baseline model for `4.43`:

- time to first action after daily triage
- percentage of prioritized members/leads touched on the same day
- actions executed per operator/day
- delay between visible risk and first follow-up

Sources remain the current platform sources:

- tasks
- audit logs
- message logs
- job/event records

No parallel spreadsheet or side ledger is allowed.

## Validation Plan

### Backend

- recommendation payload tests
- explainability rule tests
- tenant isolation tests
- approval-state transition tests
- prepared-action contract tests
- degraded-state tests

### Frontend

- inbox load / error / empty states
- explainability rendering
- item approval and rejection flows
- degraded/manual state rendering
- navigation from inbox item to operational context

### Pilot verification

- at least one real pilot walkthrough of the inbox
- evidence that approval is required item by item
- evidence that metrics can be collected against the frozen baseline

## Risks And Controls

### Risk: inbox becomes a second task system

Control:
- keep the inbox as a recommendation layer over current operational objects

### Risk: AI-first scope expands into unrelated modules

Control:
- explicitly reject coach, nutrition, wearables, and broad marketing in this phase

### Risk: recommendation quality is too opaque

Control:
- enforce `why-now` and deterministic recommendation rationale

### Risk: approval gets bypassed by convenience

Control:
- no tool in this phase may create side effects without recorded approval

## Exit Condition For Planning

This plan is complete enough when:

- engineering can implement it without reopening scope
- product can verify it remains the first AI-first operating surface only
- GSD and Spec Kit are aligned on the same slice
- implementation can begin without reopening roadmap gates
