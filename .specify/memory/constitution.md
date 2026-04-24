# AI GYM OS Constitution

## Core Principles

### I. Operational Truth Over Optimistic Surfaces
Every user-facing surface must reflect the real persisted state of the system and only expose actions the backend can actually complete. We do not ship placeholder actions, fake status, or UI promises that depend on unimplemented server behavior. If reality is partial, degraded, manual, or queued, the product must say so explicitly.

Implications:
- The backend is the source of truth for status, readiness, and eligibility.
- Dashboards, drawers, task queues, reports, and integrations must read semantically correct data, not infer truth from stale UI state.
- When a flow cannot complete automatically, the system must degrade honestly to `manual_required`, `needs_review`, or equivalent explicit states.

### II. Human Review For Risky Ingestion And High-Impact Actions
Any workflow that introduces uncertain data or triggers meaningful external effects must include an explicit human control point unless a stronger operational guarantee already exists. OCR parsing, imported sensitive data, and AI-prepared actions are never treated as final truth without review.

Implications:
- OCR parse and persistence remain separate concerns.
- Raw extracted data, confidence, and quality flags must be preserved for audit.
- AI may prepare actions, but approval policy governs execution.
- External writes to systems like Actuar, Kommo, WhatsApp, or report dispatch must be observable, retryable, and attributable.

### III. Tenant Isolation And Data Governance Are Non-Negotiable
Multi-tenant safety, PII handling, and auditability outrank local convenience. No feature, report, or automation may weaken gym isolation, expose sensitive identifiers casually, or add bypasses without explicit justification and guardrails.

Implications:
- `gym_id` scoping is the default for reads and writes.
- Cross-tenant access is allowlisted, named, and centralized.
- Sensitive flows must preserve redaction, retention, and review requirements.
- Reports, exports, OCR text, and integration payloads must follow the same governance rules as core records.

### IV. Durable Side Effects And Observable Execution
Critical side effects must be durable, inspectable, and recoverable. Work that matters operationally cannot depend on in-process background tasks, silent retries, or opaque failure modes.

Implications:
- Persist jobs before running external side effects.
- Status, attempt count, failure reason, and last transition must be inspectable.
- Flows that touch third parties or cross workflow boundaries must prefer durable jobs over ephemeral execution.
- Incident handling must preserve enough telemetry to explain what happened without guesswork.

### V. Shared Semantic Payloads Over Duplicated Rendering Logic
Complex features should expose a semantic payload once and let multiple surfaces consume it consistently. We do not maintain separate, drifting interpretations for screen, PDF, automation, and internal exports when they represent the same business artifact.

Implications:
- Premium reports, PDFs, and workspace detail views should share one semantic report model.
- Integrations should map from normalized domain fields, not from ad hoc UI-specific structures.
- Formatting belongs at the edge; domain meaning belongs in shared services and typed schemas.
- Architecture must stay extensible for future data such as segmental analysis, but hidden until real data exists.

## Product And Platform Constraints

The current product is a brownfield FastAPI + SQLAlchemy + React/Vite multi-tenant system under a controlled hardening cycle. Any work must preserve the real architecture and respect the active freeze rules.

Mandatory constraints:
- Keep the existing stack: FastAPI, SQLAlchemy, React, TypeScript, Tailwind, and the current design system.
- Preserve the canonical namespace patterns already in use, especially `members/{member_id}/body-composition*`.
- Prefer additive schema evolution and compatibility-preserving migrations over disruptive renames.
- Support desktop-first operational workflows while remaining responsive and print-ready.
- Dark mode compatibility is required for new surfaces.
- Do not invent missing physiological, medical, or segmental data.
- Do not use LLM-generated report conclusions where rules-based logic is safer and sufficient.

## Workflow And Quality Gates

Execution discipline for this repository is:
- GSD remains the execution and roadmap source of truth.
- Obsidian remains the memory, decision, incident, and handoff layer.
- Spec Kit is a complementary specification workflow, not a replacement for GSD governance.

Required delivery standards:
- Every meaningful backend change ships with focused automated validation.
- Every meaningful frontend change ships with at least smoke-level or component-level validation.
- High-risk flows must be verified in the pilot environment before being called complete.
- Parsing must be separated from final persistence.
- Premium report surfaces must be validated both as screen UX and as future PDF-ready layout.
- Freeze violations require explicit product justification, not silent scope creep.

When working in this repository:
- Prefer extending existing services and schemas over parallel architecture.
- Do not introduce speculative abstractions without a live use case.
- Keep changes cohesive across backend, frontend, tests, GSD artifacts, and operational notes.

## Governance

This constitution governs how new specs, plans, and implementations are evaluated in this repository. When local convenience conflicts with these rules, the constitution wins.

Governance rules:
- Any new spec or plan must explicitly respect multi-tenant safety, operational truth, and human-review boundaries.
- Amendments must update this file and record the reason in project memory.
- GSD artifacts, pilot evidence, and operational notes must stay aligned with the intent of this constitution.
- Features that weaken tenant isolation, hide degraded states, or bypass review for uncertain data are non-compliant until corrected.

**Version**: 1.0.0 | **Ratified**: 2026-04-14 | **Last Amended**: 2026-04-14
