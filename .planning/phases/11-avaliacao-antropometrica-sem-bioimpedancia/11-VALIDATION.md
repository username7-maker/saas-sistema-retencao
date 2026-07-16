# Phase 11 - Validation

## Commands

```text
py -3.12 -m pytest tests\test_assessment_anthropometry_service.py tests\test_assessment_anthropometry_report.py tests\test_assessment_service.py
24 passed
```

```text
py -3.12 -m pytest tests\test_assessment_anthropometry_service.py tests\test_assessment_anthropometry_report.py tests\test_assessment_service.py tests\test_body_composition.py tests\test_body_composition_anthropometry_service.py tests\test_body_composition_sync.py
77 passed
```

```text
npm.cmd test -- AnthropometricAssessmentForm.test.tsx NewAssessmentPage.test.tsx MemberProfile360Page.test.tsx MemberBodyCompositionTab.test.tsx bodyCompositionAnthropometryPreview.test.ts
21 passed
```

```text
npm.cmd run build
PASS
```

```text
npm.cmd run lint
PASS with 2 pre-existing warnings in src/pages/method/MethodOsPage.tsx
```

```text
py -3.12 -m alembic heads
20260716_0051 (head)
```

```text
py -3.12 -m alembic current
PASS - 20260716_0051 (head), after running against isolated PostgreSQL on localhost:55432
```

```text
PostgreSQL API smoke
PASS - register/login, member create, protocols, preview, create, idempotent repeat, history, PDF, DB task offsets [8,14,75,90]
```

```text
specify check
PASS - Specify CLI is ready to use
```

```text
gsd-sdk.cmd query validate.health
DEGRADED - existing baseline warnings; no new Phase 11 warning observed
```

```text
git diff --check
PASS
```

## Validation notes

- Bioimpedancia foi tratada por caracterizacao e o componente `MemberBodyCompositionTab` nao foi alterado.
- Spec 057 e Spec 058 permanecem documentadas como fases posteriores.
- Warnings de lint existentes nao foram corrigidos por estarem fora do escopo.
- Foi usado Postgres isolado em Docker (`phase11_anthro_db`, porta 55432) para fechar `alembic upgrade head`, `alembic current` e smoke de API/PDF/regua.
- O E2E legado `body-composition-anthropometry.spec.ts` foi tentado como caracterizacao nao bloqueante e falhou por texto stale do layout antigo; ele nao cobre o novo formulario manual e nenhum arquivo desse caminho foi alterado pela Phase 11.
