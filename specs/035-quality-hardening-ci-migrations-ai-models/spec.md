# Spec 035 - Quality Hardening CI, Alembic e Modelos IA

## Goal
Reduzir risco tecnico sem alterar comportamento de produto: limpar grafo Alembic, tornar CI mais confiavel, corrigir modelo especialista OpenAI e registrar risco operacional do Actuar Bridge.

## Requirements
- `OPENAI_SPECIALIST_MODEL` deve defaultar para `gpt-4.1-mini`.
- Migrations Alembic devem formar uma cadeia sem branch morto.
- Mypy deve bloquear CI.
- Pip-audit deve bloquear CI, salvo vulnerabilidades explicitamente ignoradas.
- Cobertura global permanece em 65%.
- Actuar Bridge deve manter teste/sinal para `actuar_form_changed`.

## Non-goals
- Nova feature de UI.
- Remocao de providers legados.
- Mudanca de contratos publicos.
