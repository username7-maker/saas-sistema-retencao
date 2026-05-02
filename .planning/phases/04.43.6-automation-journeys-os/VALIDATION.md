# Validacao - 04.43.6 Automation Journeys OS

## Backend

- [x] Criar jornada por template.
- [x] Preview nao cria tasks.
- [x] Ativacao inscreve apenas pessoas do tenant.
- [x] Job cria uma task por etapa vencida.
- [x] Job nao duplica task/evento em execucao repetida.
- [x] Outcome da task atualiza enrollment e cria evento de jornada.
- [x] Trainer nao acessa jornada financeira/comercial.

## Frontend

- [x] `/automations` abre em `Jornadas prontas`.
- [x] Usuario consegue ver templates prontos.
- [x] Preview mostra elegiveis e amostra.
- [x] Ativar jornada atualiza lista.
- [x] `Regras avancadas` preserva automacoes antigas.
- [x] `ai_evaluate` nao aparece como promessa falsa.

## Evidencias Locais

- `pytest tests/test_automation_journeys.py tests/test_automation_engine.py tests/test_work_queue_service.py tests/test_health.py -q`: 37 passed.
- `npm.cmd run build`: build concluido.
- `specify check`: OK.
- `alembic heads`: `20260428_0036`.

## Piloto

- [ ] Ativar onboarding, retencao e inadimplencia.
- [ ] Executar 30 acoes pela Work Queue.
- [ ] Medir tempo medio por acao e outcomes.
