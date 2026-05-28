# Validacao - 09.5

## Criterios
- `alembic branches` nao mostra branchpoints.
- `alembic heads` mostra uma unica head.
- `OPENAI_SPECIALIST_MODEL` default e fallback usam `gpt-4.1-mini`.
- Backend CI nao usa `|| true` em mypy e pip-audit.
- Cobertura global continua com `--cov-fail-under=65`.
- `actuar_form_changed` permanece testavel/monitoravel.

## Resultados
Executado em 2026-05-20.

| Comando | Resultado |
| --- | --- |
| `railway.cmd run --service ai-gym-os-api --environment production alembic current` | `20260515_0045 (head)` |
| `alembic branches; alembic heads` | Sem branchpoints; uma head `20260515_0045` |
| `python -m compileall app/core/config.py app/services/ai_prompt_registry_service.py` | Passou |
| `mypy app/ --config-file mypy.ini` | Passou: 253 arquivos |
| `ruff check app tests --select E9,F63,F7,F82` | Passou |
| `bandit -r app/ -ll -q` | Passou; apenas aviso `nosec` existente em `app/entrypoint.py` |
| `pip-audit --strict --desc on --ignore-vuln PYSEC-2025-185 -r requirements.txt` | Passou: 0 vulnerabilidades novas, 1 ignorada explicitamente |
| `pytest -q --tb=short tests/test_auth_service.py ... tests/test_tenant_fk_guards.py` | Passou: 65 testes |
| `pytest -q --tb=short tests/test_actuar_browser_client.py tests/test_body_composition_sync.py` | Passou: 49 testes |
| `pytest -q --tb=short --cov=app --cov-report=term-missing --cov-fail-under=65` | Passou: 1009 testes, cobertura 66.68% |

## Nota de seguranca
`PYSEC-2025-185` permanece documentado porque `pip-audit` nao informa versao corrigida para `python-jose`, mesmo em `3.5.0`. O CI nao usa mais `|| true`; ele ignora apenas esse ID conhecido.
