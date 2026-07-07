# 09.21 - Validation

## Planned Gates
- `specify check` - passed before and after implementation.
- `py -3.12 -m pytest -q saas-backend/tests/test_body_composition_anthropometry_service.py` - 9 passed.
- `npm.cmd test -- src/test/bodyCompositionAnthropometryPreview.test.ts src/test/BodyCompositionReportPage.test.tsx` - 9 passed.
- `npm.cmd run lint` - passed with 2 existing warnings in `MethodOsPage.tsx`.
- `npm.cmd run build` - passed.
- `git diff --check` - passed with CRLF warnings only.

## Deployment Gates
- Vercel production deploy para `saas-frontend-pearl.vercel.app`
- Railway deploy do backend `ai-gym-os-api`
- Smoke HTTP do frontend, assets de mapa e backend `/health`/`/health/ready`
