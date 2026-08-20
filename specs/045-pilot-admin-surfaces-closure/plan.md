# Implementation Plan: Pilot Admin Surfaces Closure

## Technical Context

- Backend: FastAPI, SQLAlchemy, jobs duraveis, Resend via `app.utils.email`.
- Frontend: React/Vite, TanStack Query, Cordex/Lovable shell.
- Planning: GSD continua como execucao; Spec Kit formaliza escopo.

## Scope V1

1. Corrigir `send_monthly_reports` para respeitar `gym_id` do job.
2. Cobrir regressao de tenant no servico de relatorios.
3. Atualizar GSD/Obsidian apontando que a Phase 4.34 foi reaberta como `09.15`.
4. Rodar `specify check` e testes focados de relatorios.

## Validation

- `specify check`
- `pytest tests/test_report_service.py tests/test_reports_router.py`
- Busca manual por envio mensal sem filtro de tenant.

## Deployment

Sem deploy automatico neste corte ate os testes focados passarem. Publicacao no piloto deve acontecer depois de validacao local e confirmacao de que as variaveis Resend seguem configuradas no Railway.
