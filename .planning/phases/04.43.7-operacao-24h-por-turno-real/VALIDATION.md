# Validacao - 04.43.7 Operacao 24h

## Backend

- `normalize_preferred_shift("madrugada") == "overnight"`.
- Check-in 02h entra em `overnight`.
- Check-in 07h entra em `morning`.
- Usuario pode ser criado/editado com `work_shift=overnight`.
- Work Queue com `shift=overnight` filtra madrugada.
- `my_shift` de usuario madrugada retorna itens madrugada.
- Cleanup preview nao altera dados.
- Cleanup apply grava `extra_data.operational_archive`.
- Inadimplencia, jornada e onboarding D0-D30 ficam protegidos.

## Frontend

- `Madrugada` aparece em usuarios, membros, CRM, tasks, retencao e avaliacoes.
- Fila de execucao continua padrao por `Meu turno`.
- Owner/manager consegue ver preview de saneamento antes de arquivar.

## Piloto

- Configurar pelo menos um usuario em cada turno.
- Recalcular turnos dos alunos.
- Arquivar ruido operacional por preview/aplicar.
- Validar lote diario de ate 25 acoes por operador.

## Evidencia local

- Backend: `pytest saas-backend/tests/test_preferred_shift_service.py saas-backend/tests/test_task_service.py saas-backend/tests/test_work_queue_service.py saas-backend/tests/test_user_admin_routes.py saas-backend/tests/test_member_service_full.py saas-backend/tests/test_retention_dashboard_queue.py saas-backend/tests/test_assessment_queue_service.py -q` -> 69 passed.
- Frontend build: `npm run build` -> passou.
- Frontend focused tests: `npm test -- --run src/test/preferredShift.test.ts src/test/TasksPage.test.tsx src/test/UsersPage.test.tsx src/test/MembersPage.test.tsx src/test/AssessmentsPage.test.tsx` -> 23 passed.
- Spec Kit: `specify check` -> CLI pronto.
