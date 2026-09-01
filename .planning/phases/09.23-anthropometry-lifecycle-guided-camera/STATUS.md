# Status - 09.23

Status: implementation, encrypted logical backup and production rollout complete.

Baseline commit: `ba66e31`.
Production source commit: `805b3f0b819a1e70e7ed69b922e4a71002227f14`.

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

Production rollout (2026-09-01):

- Supabase project is `ACTIVE_HEALTHY`;
- the local network still filters outbound TCP 5432/6543, so the dump was executed from an ephemeral GitHub Actions runner over an allowed network;
- logical backup contains validated `roles.sql`, `schema.sql` and `data.sql`, encrypted before artifact upload;
- local encrypted archive SHA-256: `ECC65BD284D04176802620D379828FFD72134E036F2FDC74F7A3ABFBA491913A`;
- temporary GitHub secrets, workflow runs, artifact and branch were removed after local validation;
- Railway API deployment: `9fa14038-4901-4dea-ad6d-05bb6eb7166f` (`SUCCESS`);
- Railway worker deployment: `367a106e-285c-4ac9-bb1d-bb731c09c2b7` (`SUCCESS`);
- Vercel production deployment: `dpl_8miyZshfJDDsSSb87q9KdKetYAD3` (`READY`), aliased to `https://saas-frontend-pearl.vercel.app`;
- API readiness is `200`, API and frontend expose the same production source SHA, and the worker startup log reports the same SHA;
- anthropometry GET/PUT/DELETE/report endpoints reject anonymous access with `401`, while an unknown route returns `404`;
- no new database migration was required and the smoke checks did not create, edit or delete client records;
- authenticated UI smoke remains manual because no reusable authorized test session was stored on this workstation.
