# Status - 09.23

Status: implementation and focused validation complete; production rollout blocked at backup gate.

Baseline commit: `ba66e31`.

Delivered locally:

- scoped anthropometry detail/update/soft-delete/report APIs;
- server-side recomputation, optimistic concurrency and before/after audit;
- manual Actuar follow-up tasks without automatic external mutation;
- premium anthropometry web report, PDF/print, same-method history, edit/delete actions and ISO date fix;
- guided camera with high-resolution rear-camera preference, device switching, capability-aware torch/zoom, review, crop, rotation, normalization and quality warnings;
- release SHA exposure in frontend, API and worker;
- versioned Cordex x AFIG product/engineering benchmark.

Validation:

- backend focused: 38 passed;
- frontend focused: 28 passed;
- frontend lint: 0 errors (2 pre-existing warnings in `MethodOsPage.tsx`);
- frontend production build: passed;
- full backend: 1234 passed, 1 unrelated baseline failure in `test_body_composition_ai_service.py`;
- full frontend: 206 passed, 7 unrelated baseline expectation failures; the audit spec also requires external URL variables.

Rollout gate:

- Supabase project is `ACTIVE_HEALTHY`;
- Railway API/worker and Vercel identities are linked and online;
- logical backup is blocked because TCP connections to the Supabase pooler time out on ports 5432 and 6543 from this workstation;
- the Free plan exposes no downloadable physical backup (`supabase backups list` returned no backup entries);
- no database migration is required by this phase and no production data has been changed;
- do not deploy until a logical backup succeeds from an allowed network or a managed backup is available.
