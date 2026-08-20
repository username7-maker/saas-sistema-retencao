# Plan 035 - Quality Hardening

## Implementation
- Atualizar config e prompt registry para modelo especialista valido.
- Atualizar env/docs para o novo default.
- Remover migration redundante e ajustar merge migration dependente.
- Adicionar `mypy.ini` e tornar mypy bloqueante.
- Tornar pip-audit bloqueante.
- Registrar no GSD/Obsidian que Actuar Bridge depende de seletores externos e precisa monitoramento.

## Verification
- Executar checks Alembic.
- Executar compile/testes backend.
- Executar mypy.
- Executar pip-audit quando ferramenta estiver disponivel.
