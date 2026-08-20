# Open Loops

## 2026-05-20 - Cobertura Kommo por dominio
Validar na ProGym quais pipelines, etapas, Salesbots e campos customizados existem para `retention`, `onboarding`, `assessment`, `body_composition`, `finance`, `sales`, `student_ai` e `support`.

## Kommo ProGym
- Confirmar ids de pipeline, etapa, Salesbot e campos customizados para `body_composition`, `retention`, `onboarding`, `finance`, `sales`, `student_ai` e `support`.
- Validar se o token da Kommo possui escopo `files`.
- Validar se o Salesbot configurado consegue enviar o arquivo anexado no lead ao aluno pelo canal conectado.

## Copy Agent Operacional
- Validar 20 mensagens reais de retencao/onboarding com a recepcao antes de confiar no tom.
- Conferir se `OPENAI_SPECIALIST_MODEL=gpt-4.1-mini` esta configurado no piloto.
- Medir se a equipe usa `Regenerar rascunho` ou prefere template seguro.

## Quality Hardening
- Manter `alembic branches` vazio em toda nova migration.
- Revisar output do `pip-audit` quando uma vulnerabilidade exigir `--ignore-vuln`.
- Elevar cobertura dos caminhos criticos de auth, tenant isolation e security sem travar a entrega global.
- Monitorar ocorrencias de `actuar_form_changed` como sinal de quebra do Actuar Bridge.
# Open Loop - 09.6 Cordex Command Center

- Validar visualmente login, shell, dashboard executivo e dashboards principais apos build.
- Planejar proxima onda para tarefas, avaliacoes, membros, CRM, settings e relatorios.
