# VALIDATION - 09.18 Body Composition Anthropometry V1

## Checklist

- [x] `specify check`
- [x] migration cria campos e faz backfill legado
- [x] calculo masculino usa abdomen antes de cintura
- [x] calculo feminino nao troca cintura por abdomen automaticamente
- [x] GeneOS inconsistente exige revisao antes de virar oficial
- [x] relatorio/PDF usam `body_fat_used_percent`
- [x] IA usa contexto de fonte e nao trata percentual como diagnostico
- [x] Actuar nao recebe novos campos de perimetria
- [x] frontend mostra fonte, metodo, faixa, confianca e alertas
- [x] busca final por usos oficiais indevidos de `body_fat_percent`
- [x] Playwright visual do relatorio web com antropometria como fonte oficial

## Evidencia

- `specify check` passou em 2026-07-07.
- `git diff --check` passou, apenas avisos LF/CRLF do Git no Windows.
- `py -3.12 -m compileall -q .\saas-backend\app .\saas-backend\alembic\versions\20260707_0048_body_composition_anthropometry_v1.py` passou.
- `py -3.12 -m alembic heads` retornou `20260707_0048 (head)`.
- `py -3.12 -m pytest -q saas-backend\tests\test_body_composition_anthropometry_service.py saas-backend\tests\test_body_composition.py saas-backend\tests\test_body_composition_ai_service.py saas-backend\tests\test_body_composition_image_parse_service.py` passou: 45 passed, 2 warnings.
- `py -3.12 -m pytest -q saas-backend\tests\test_body_composition_anthropometry_service.py saas-backend\tests\test_body_composition.py saas-backend\tests\test_body_composition_ai_service.py` passou apos reforco da regra oficial: 31 passed, 2 warnings.
- `npm.cmd test -- src/test/bodyCompositionAnthropometryPreview.test.ts src/test/MemberBodyCompositionTab.test.tsx src/test/BodyCompositionReportPage.test.tsx src/test/bodyCompositionInterpretation.test.ts src/test/bodyCompositionOcr.test.ts` passou: 5 files, 24 tests.
- `npx.cmd eslint` no escopo da feature passou sem erros; ficou 1 warning existente de `watch()`/React Hook Form em `MemberBodyCompositionTab`.
- `npm.cmd run build` passou.
- `npx.cmd playwright test tests/e2e/body-composition-anthropometry.spec.ts --project=chromium` passou: 1 test.
- Evidencia visual: `.planning/phases/09.18-body-composition-anthropometry-v1/evidence/body-composition-report-source-panel.png`.

## Observacoes

- `npm.cmd run lint` completo ainda falha por erros globais preexistentes de React Compiler (`react-hooks/set-state-in-effect`) em varios arquivos fora do escopo desta feature. O erro de pureza em `BodyCompositionReportPage` foi corrigido.
- `body_fat_percent` permanece em OCR, compatibilidade, Actuar e exibicao bruta rotulada. Usos oficiais foram migrados para `body_fat_used_percent` no escopo de relatorio, PDF, IA, WhatsApp/Kommo e cards principais.
- Auditoria de paridade registrada em `ACTUAR-PARITY-AUDIT.md`.
- Pos-auditoria: `manual_override` passou a ter `measurement_source` proprio; snapshot de IA pessoal nao exporta mais `body_fat_percent` como campo ambiguo.
- Revalidacao pos-auditoria:
  - `specify check` passou.
  - `git diff --check` passou, apenas avisos LF/CRLF do Git no Windows.
  - `py -3.12 -m pytest -q saas-backend\tests\test_body_composition_anthropometry_service.py saas-backend\tests\test_personal_ai_service.py saas-backend\tests\test_body_composition.py saas-backend\tests\test_body_composition_ai_service.py` passou: 39 passed, 2 warnings.
  - `npm.cmd test -- src/test/bodyCompositionAnthropometryPreview.test.ts src/test/MemberBodyCompositionTab.test.tsx src/test/BodyCompositionReportPage.test.tsx src/test/bodyCompositionInterpretation.test.ts src/test/bodyCompositionOcr.test.ts` passou: 24 tests.
  - `npx.cmd eslint` no escopo da feature passou sem erros, com 1 warning conhecido de React Hook Form `watch()`.
  - `npm.cmd run build` passou.
  - `npx.cmd playwright test tests/e2e/body-composition-anthropometry.spec.ts --project=chromium` passou: 1 test.
  - `MemberBodyCompositionTab` agora tem teste cobrindo checklist do protocolo e comparativo bilateral ao editar avaliacao existente.
