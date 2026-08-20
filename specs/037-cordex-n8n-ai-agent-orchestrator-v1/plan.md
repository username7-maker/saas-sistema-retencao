# Plan 037 - Cordex WhatsApp AI Agent V1

## Technical Plan

1. Revisar a fase/spec existente em vez de criar feature paralela.
2. Reorientar `/n8n` para WhatsApp-first.
3. Criar `00-whatsapp-agent-router` como entrada n8n acionada pelo backend.
4. Separar `01-whatsapp-internal-operator-agent` e `02-whatsapp-external-service-agent`.
5. Criar `03-whatsapp-send-reply` para preservar envio via backend.
6. Manter tools operacionais como sub-workflows: web search, email, calendar, CRM, RAG, DB safe query, task manager, WhatsApp policy, approval, audit, reports e n8n workflow manager.
7. Adicionar servico backend para chamar n8n, validar resposta e evitar duplicidade com fallback legado.
8. Adicionar endpoint backend protegido para reply do agente.
9. Atualizar prompts, schema, docs, env e testes para canal primario WhatsApp.
10. Criar/atualizar drafts inativos no n8n e registrar IDs.

## Risk Control

- Nada sera ativado em producao automaticamente.
- Nenhum token, senha ou chave sera hardcoded.
- `WHATSAPP_AGENT_MODE=sandbox` nao envia reply real do agente.
- O n8n nao chama Evolution diretamente na V1.
- Fluxo externo responde apenas ao mesmo remetente.
- Broadcast fica bloqueado.
- SQL destrutivo fica bloqueado ou pendente de aprovacao.
- Acoes destrutivas, envio externo sensivel, alteracao de producao e dados sensiveis exigem approval gate.
