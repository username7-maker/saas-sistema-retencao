# Cordex Gym OS Agent Development Guide

## Ruflo Role

Ruflo is a development orchestration tool for this repository. It is not a product runtime dependency and must not be added to the SaaS backend/frontend production stack unless a dedicated architecture decision approves it.

Use Ruflo concepts to improve engineering execution:

- route development tasks to the right agent role;
- detect test gaps before implementation is considered done;
- coordinate large refactors with explicit ownership;
- record reusable patterns from successful phases;
- strengthen security/safety reviews around AI prompts, webhooks and tenant isolation;
- track AI/tooling cost when running large agent workflows.

## Source Of Truth

- GSD is the execution system.
- Spec Kit is the formal spec contract.
- Obsidian/planning docs are the memory of decisions.
- Ruflo is a development accelerator layered on top of that workflow.

Do not let Ruflo-generated plans override existing GSD/Spec Kit artifacts without updating the corresponding phase/spec.

## Default Development Flow

1. Read the active GSD phase and Spec Kit spec before editing.
2. Use Ruflo-style routing only to decide the right work mode: backend, frontend, tests, security, documentation, deploy.
3. Keep implementation local and explicit. Do not spawn broad autonomous work without clear file ownership.
4. After edits, run focused tests and the relevant lint/build checks.
5. Record any durable decision in the phase docs, Spec Kit or Obsidian memory files.

## Guardrails

- Never add Ruflo packages to `saas-backend` or `saas-frontend` runtime dependencies for normal feature work.
- Never let an agent write across backend/frontend/planning/docs at once without a phase plan.
- Never auto-apply generated code that touches auth, tenant isolation, LGPD, payment, Kommo, WhatsApp or AI safety without tests.
- Treat AI-generated suggestions as drafts until verified by code, tests and product intent.

## Useful Local References

- Ruflo clone: `C:\aigymos\external\ruflo`
- Development workflow: `docs/ruflo-development-workflow.md`
- Adoption notes: `docs/ruflo-adoption.md`

