# Validação

## Cenários Obrigatórios

1. Aluno D1 com D7/D15/D30 futuras não perde score por tasks futuras.
2. Avaliação anterior à matrícula não conta como primeira avaliação do onboarding.
3. WhatsApp/NPS anterior à matrícula não conta como resposta do onboarding.
4. Handoff D30 roda entre D30 e D37 e não duplica.
5. `TRAINER` acessa score detalhado.
6. `onboarding_service` não duplica etapas se a jornada canônica já materializou tasks.
7. Tasks futuras têm `work_queue_visible_from` e ficam fora do `Fazer agora`.
8. Check-in/avaliação/WhatsApp fecham apenas etapas compatíveis.
9. Mensagem sensível escala para humano.
10. Tenant isolation preservado.

## Execução Local

- `python -m pytest saas-backend\tests\test_onboarding_score.py saas-backend\tests\test_onboarding_service.py saas-backend\tests\test_onboarding_dedup.py saas-backend\tests\test_members_onboarding_scoreboard_router.py` - passou.
- `python -m pytest saas-backend\tests\test_assessment_service.py` - passou.
- `python -m pytest saas-backend\tests\test_autopilot_services.py` - passou.
- `python -m compileall saas-backend\app` - passou.
- `npm.cmd run build` em `saas-frontend` - passou.
- `specify check` - CLI pronto.
