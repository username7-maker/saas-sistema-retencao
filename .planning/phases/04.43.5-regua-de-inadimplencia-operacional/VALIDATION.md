# Validation

## Backend

- Recebivel vencido de aluno ativo materializa task.
- Reprocessar a regua atualiza task aberta em vez de duplicar.
- Stage D+7/D+15 altera prioridade e cria evento.
- Outcomes financeiros funcionam no Work Queue:
  - `payment_confirmed` conclui;
  - `payment_promised` adia;
  - financeiro preserva dominio `finance`.

## Frontend

- Build de producao passou.
- Modo execucao possui botoes financeiros.
- Dashboard financeiro consulta summary e aciona materializacao.

## Testes Executados

```bash
pytest tests/test_work_queue_service.py tests/test_delinquency_service.py -q
npm.cmd run build
```

## Proxima Validacao Manual

- Criar dois recebiveis vencidos para o mesmo aluno e confirmar uma unica task agregada.
- Abrir `/tasks` como receptionist e registrar `Prometeu pagar`.
- Abrir `/tasks` como trainer e confirmar ausencia de financeiro.
- Abrir dashboard financeiro e executar `Atualizar regua`.
