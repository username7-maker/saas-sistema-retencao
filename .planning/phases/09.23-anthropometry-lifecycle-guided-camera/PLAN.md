# Phase 09.23 - Anthropometry lifecycle and guided camera

## Objective

Give manual anthropometry the same core lifecycle as bioimpedance: a premium web
presentation, safe editing, recoverable deletion and same-method history. Replace
the basic receipt camera with a capability-aware guided scanner and document the
product/engineering maturity gap between Cordex and AFIG without comparing client
results or reverse engineering the external product.

## Delivery

1. Add scoped detail, update, soft-delete and report endpoints for anthropometry.
2. Recalculate all derived values on update, guard concurrent edits and audit the
   before/after state.
3. Reconcile only open generated tasks; create an explicit manual Actuar follow-up
   for updates and deletions.
4. Reuse the premium body report for a dedicated anthropometry web route and keep
   comparisons restricted to manual anthropometry history.
5. Add history actions and hydrate the registration form for editing.
6. Replace the camera modal with a guided, capability-aware capture and review flow.
7. Publish a P0/P1/P2 Cordex x AFIG product and engineering benchmark.
8. Validate focused/full tests, production builds and authenticated smoke before a
   synchronized Railway API/worker and Vercel rollout from one clean commit.

## Safety invariants

- Never hard-delete a member or assessment.
- Never accept client-supplied calculation origins or derived results.
- Never compare anthropometry and bioimpedance as equivalent methods.
- Never mutate completed/manual tasks when an assessment changes.
- Never automate Actuar update/delete in this phase.
- Never persist captured images beyond the existing OCR request lifecycle.

