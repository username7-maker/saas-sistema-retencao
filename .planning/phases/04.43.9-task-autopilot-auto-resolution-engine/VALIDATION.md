# Validation - 04.43.9 Task Autopilot

## Validacoes tecnicas

- `python -m compileall app` no backend: PASS.
- `npm.cmd run build` no frontend: PASS.
- `specify check`: PASS.
- `alembic heads`: PASS, head atual `20260503_0037`.
- `python -m pytest tests\test_autopilot_services.py -q`: PASS, 4 testes.
- `python -m pytest tests\test_work_queue_service.py tests\test_task_event_service.py tests\test_scheduler_jobs.py -q`: PASS, 22 testes.
- `alembic upgrade head`: pendente quando houver banco piloto/local apontado com `DATABASE_URL`.

## Validacao manual

1. Ativar `autopilot_enabled=true`, `autopilot_auto_close_enabled=true`, `autopilot_auto_send_enabled=false`.
2. Criar task de retencao para aluno.
3. Registrar check-in do aluno.
4. Confirmar task fechada via `TaskEvent` com fonte `autopilot`.
5. Criar task financeira, marcar recebivel como `paid` e confirmar fechamento.
6. Usar `Enviar e aguardar` em uma task com telefone e confirmar `AutopilotAction.awaiting_outcome`.
7. Registrar inbound WhatsApp simples e confirmar outcome `responded`.
8. Registrar inbound com "quero cancelar" e confirmar escalonamento humano.
