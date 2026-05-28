# Spec 037 - Cordex WhatsApp AI Agent V1

## User Story

Como equipe Cordex, quero um agente de IA WhatsApp-first no n8n que receba mensagens normalizadas pelo backend, diferencie equipe interna de leads/alunos, responda ou crie handoff com seguranca e registre tudo sem duplicar o fluxo legado de WhatsApp.

## Requirements

- O backend deve continuar recebendo Evolution API em `/api/v1/whatsapp/webhook`.
- O backend deve ignorar grupo, `fromMe`, payload sem telefone/texto e instancia desconhecida.
- O backend deve normalizar o payload e chamar o n8n em `N8N_WHATSAPP_AGENT_WEBHOOK_URL`.
- O backend deve classificar `audience=internal` para numeros em `WHATSAPP_INTERNAL_ALLOWED_PHONES`; os demais entram como `external`.
- O n8n deve ter um roteador principal `00-whatsapp-agent-router`.
- O n8n deve ter dois fluxos separados: agente interno operacional e agente externo controlado.
- O agente externo deve responder somente ao mesmo remetente.
- O n8n deve retornar contrato estruturado com `status`, `action`, `recipient_phone`, `message`, `risk`, `approval_required` e `metadata`.
- O backend deve usar `send_whatsapp_sync` para envio final quando `WHATSAPP_AGENT_MODE=active`.
- O n8n nao deve enviar direto pela Evolution na V1.
- Falha do n8n deve acionar fallback legado apenas quando `WHATSAPP_AGENT_FALLBACK_TO_LEGACY_NURTURING=true`.
- Ferramentas sensiveis devem passar por approval gate.
- RAG deve usar OpenAI embeddings com pgvector por padrao.
- Logs, memoria, permissoes, tarefas e eventos WhatsApp devem persistir em Postgres.
- Workflows devem ser importaveis, legiveis, inativos por padrao e sem credenciais hardcoded.

## Non-Goals

- Ativar workflows em producao automaticamente.
- Configurar credenciais reais.
- Enviar mensagens reais em modo sandbox.
- Fazer o n8n substituir o backend como dono da Evolution API.
- Criar robo externo irrestrito para leads/alunos.

## Acceptance Criteria

- `/n8n` contem router WhatsApp, agente interno, agente externo, send reply via backend, tools, prompts, SQL, README, security guide e test plan.
- Existe endpoint/backend service para chamar o n8n e aplicar fallback legado sem duplicidade.
- Existe endpoint backend protegido para reply do agente.
- Existe workflow de aprovacao humana.
- Existe workflow de auditoria.
- Existe schema Postgres para sessoes, mensagens, memoria, tool calls, aprovacoes, documentos, chunks, roles, politicas, tarefas e eventos WhatsApp.
- E possivel criar drafts inativos no n8n.
- Integracoes sem credencial real ficam explicitamente como placeholders seguros.
