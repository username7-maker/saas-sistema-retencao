# Validation - 04.43.8 Regua Retencao e Reativacao

## Validado localmente

- `python -m pytest tests/test_retention_stage_service.py tests/test_retention_dashboard_queue.py tests/test_work_queue_service.py -q`
- Resultado: 24 passed.

- `npm.cmd run build`
- Resultado: build concluido com sucesso.

- `npm.cmd test -- RetentionDashboardPage.test.tsx`
- Resultado: 4 passed.

- `python -m pytest tests/test_retention_intelligence.py tests/test_task_list_enrich.py -q`
- Resultado: 16 passed.

- `specify check`
- Resultado: Specify CLI pronto para uso.

## Cenarios cobertos

- 5 dias -> `monitoring`.
- 10 dias -> `attention`.
- 20 dias -> `recovery`.
- 35 dias -> `reactivation`.
- 50 dias -> `manager_escalation`.
- 65 dias -> `cold_base`.
- Endpoint de fila encaminha filtro `retention_stage`.
- Work Queue continua passando nos testes focados.

## Pendente no piloto

- Validar uma lista real de alunos `30+`.
- Executar 10 acoes de reativacao e registrar outcomes.
- Confirmar que `cold_base` nao trava a fila diaria.
- Confirmar que recepcao/professor entendem diferenca entre prevencao e reativacao.
