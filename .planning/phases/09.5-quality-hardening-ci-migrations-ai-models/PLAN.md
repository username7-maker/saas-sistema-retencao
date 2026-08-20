# Plano - 09.5 Quality Hardening

## Backend / Config
- Trocar default de `openai_specialist_model` e fallback do prompt registry para `gpt-4.1-mini`.
- Documentar `OPENAI_SPECIALIST_MODEL=gpt-4.1-mini` nos exemplos de ambiente.
- Atualizar docs do prompt registry para evitar que agentes futuros reinstalem `gpt-5.4-mini`.

## Alembic
- Remover `20260424_0020_add_trainer_role.py`, redundante com `20260323_0023_add_trainer_role.py`.
- Ajustar `20260427_0035_add_task_events.py` para revisar apenas `20260426_0034`.
- Validar `alembic branches` vazio e `alembic heads` com uma head.

## CI
- Adicionar `saas-backend/mypy.ini`.
- Substituir mypy consultivo por check bloqueante.
- Remover supressao total do `pip-audit`.
- Atualizar dependencias com vulnerabilidades corrigidas.
- Ignorar explicitamente apenas `PYSEC-2025-185`, sem fix version publicada para `python-jose`.
- Manter cobertura global em 65%.

## Actuar Bridge
- Registrar a fragilidade de seletores como risco monitorado.
- Validar que testes/sinais de `actuar_form_changed` continuam presentes.

## Validacao
- `python -m compileall app/core/config.py app/services/ai_prompt_registry_service.py`
- `alembic branches`
- `alembic heads`
- `mypy app/ --config-file mypy.ini`
- `pip-audit --strict --desc on --ignore-vuln PYSEC-2025-185 -r requirements.txt`
- `pytest -q --tb=short --cov=app --cov-report=term-missing --cov-fail-under=65`
