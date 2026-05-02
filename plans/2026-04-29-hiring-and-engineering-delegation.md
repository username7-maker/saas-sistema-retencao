# Hiring And Engineering Delegation Plan

Date: 2026-04-29
Owner: CEO
Source issue: COR-1

## Company Mission

Help small and mid-sized entrepreneurs improve their businesses using AI and company-built software. Current product focus is AI GYM OS: an operational SaaS for gyms covering retention, CRM, tasks, assessments, premium reports, and AI-assisted daily triage.

## Hiring Decision

Hire the first engineering leader as CTO / Founding Engineer.

Rationale:

- The immediate roadmap is mostly technical: brownfield FastAPI, SQLAlchemy, PostgreSQL, React, Vite, jobs, tenant isolation, PII, and AI workflow surfaces.
- The CEO should set priority and delegation, not implement code.
- The company has no technical direct report yet, so all code, bug, feature, infra, and devtools work needs a CTO owner.

Initial role:

- Name: CTO
- Title: Founding Engineer / Chief Technology Officer
- Reports to: CEO
- Scope: technical roadmap decomposition, architecture, implementation quality, and execution.
- Limits: no company strategy, marketing, pricing, or unsupervised destructive production operations.

## Operating Priorities

1. Keep the product honest for pilot operations: no demo data or optimistic UI where the backend cannot support the action.
2. Protect tenant isolation, PII, session safety, and auditability before expanding scope.
3. Advance the active v3.3 workstream around `lead-member-context-v1` only in narrow, verified slices.
4. Keep paused v3.2 Phase 5 and Phase 6 work blocked until the hardening/freeze gates are explicitly reopened.
5. Ask the CEO to hire UX, QA, Security, or CMO only when the CTO has a concrete need and acceptance criteria.

## Delegated Work

### CTO Task 1: Convert Roadmap Into Engineering Backlog

Objective: read the current roadmap and produce a concrete engineering issue tree for the next execution window.

Acceptance criteria:

- Identify the top three technical slices from `.planning/STATE.md`, `.planning/ROADMAP.md`, and active phase/spec files.
- For each slice, define objective, dependencies, acceptance criteria, verification, and likely owner.
- Create child issues for work that is ready to execute.
- Leave a CEO-facing comment naming what should happen next.

### CTO Task 2: Start Active v3.3 Technical Execution

Objective: start the next actionable slice around consuming `lead-member-context-v1` in operational surfaces.

Acceptance criteria:

- Confirm the current implementation state from the code and planning docs.
- Select the smallest high-value surface or API contract gap.
- Implement directly if narrow enough; otherwise create narrower child issues.
- Run focused verification and report residual risk.

## Follow-Up Rules

- CEO will not implement code.
- CTO owns technical decomposition and execution.
- If CTO is blocked by missing design, QA, security, or marketing capacity, CTO must create a clear escalation to CEO with the requested hire or review scope.
- Parent onboarding issue can close only after the CTO hire exists, the plan is durable, and at least one technical workstream is delegated with a clear next action.
