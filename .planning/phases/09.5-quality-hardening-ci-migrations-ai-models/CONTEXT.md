# 09.5 - Quality Hardening: Alembic, CI e Modelos de IA

## Contexto
Uma auditoria pontual encontrou problemas de qualidade que nao mudam o produto, mas aumentam risco tecnico: branch redundante no grafo Alembic, CI permissivo com `|| true`, default de modelo OpenAI inexistente e monitoramento incompleto para fragilidade do Actuar Bridge.

## Objetivo
Endurecer a base de entrega antes de avancar roadmap: Alembic com uma cadeia limpa, checks de CI bloqueantes, modelo especialista valido e risco do Actuar Bridge registrado/validavel.

## Fora de escopo
- Criar nova feature de produto.
- Renomear chaves tecnicas persistentes.
- Remover Claude ou fluxos legados.
- Alterar schema publico de APIs.

## Decisoes
- `OPENAI_SPECIALIST_MODEL` passa a usar `gpt-4.1-mini` por default.
- Migration redundante de trainer role pode ser removida porque o piloto foi confirmado em `20260515_0045 (head)`.
- Mypy e pip-audit deixam de ser apenas consultivos.
- Cobertura global continua em 65%, com caminho para elevar checks criticos.
