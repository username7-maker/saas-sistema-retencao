# Phase 4: Import mapper e reconciliacao manual - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `04-CONTEXT.md`.

**Date:** 2026-03-24
**Phase:** 04-import-mapper-e-reconciliacao-manual
**Mode:** auto
**Areas discussed:** preview entry point, mapping model, operator safety, scope boundaries

---

## Preview entry point

| Option | Description | Selected |
|--------|-------------|----------|
| Mapper after preview | Reuse current validate-first flow and open reconciliation only after initial preview | x |
| Separate step before preview | Add a brand-new stage before validation | |
| Full wizard | Split upload, mapping, validation and commit in a longer multi-step flow | |

**User's choice:** Auto-selected recommended default.
**Notes:** Reusing the current preview contract keeps the phase narrow and aligned with `ImportsPage.tsx`.

---

## Mapping model

| Option | Description | Selected |
|--------|-------------|----------|
| Assisted mapper | Map source column to supported canonical field or ignore it | x |
| Free-form ETL | Allow arbitrary expressions and transformations | |
| Hard template only | Reject every non-template file and provide no manual reconciliation | |

**User's choice:** Auto-selected recommended default.
**Notes:** The current backend already has aliases and strong parsers; this phase adds reconciliation, not a generic import engine.

---

## Operator safety

| Option | Description | Selected |
|--------|-------------|----------|
| Re-run preview after mapping | Recompute impact before enabling final commit | x |
| Apply mapping only on final commit | Let operator confirm without seeing reconciled preview | |
| Silent auto-fix | Accept mapper edits and assume commit is safe without another preview | |

**User's choice:** Auto-selected recommended default.
**Notes:** Safety stays anchored in preview-first behavior already established in the product.

---

## Scope boundaries

| Option | Description | Selected |
|--------|-------------|----------|
| File-session only | No saved templates, no custom transforms, no fuzzy new engine in this phase | x |
| Save reusable templates | Persist mapping templates per gym in this same phase | |
| Full import studio | Combine templates, transforms and reconciliation in one cycle | |

**User's choice:** Auto-selected recommended default.
**Notes:** Templates and larger import ergonomics remain valid future work, but would dilute the operational goal of Phase 4.

---

## the agent's Discretion

- Exact UI shape of the mapper inside `ImportsPage.tsx`
- Exact payload encoding strategy for preview/import endpoints

## Deferred Ideas

- Saved mapping templates
- Advanced transformation rules
- Rich fuzzy reconciliation heuristics
