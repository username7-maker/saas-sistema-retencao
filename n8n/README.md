# Cordex WhatsApp AI Agent V1 no n8n

Este pacote cria a V1 do agente de IA WhatsApp-first da Cordex no n8n. O backend continua sendo o dono do webhook Evolution API, do tenant, dos logs, do rate limit, do status da instancia e do envio final. O n8n atua como cerebro de IA/politica: recebe um payload normalizado do backend, decide a resposta ou o handoff e devolve um contrato simples para o backend executar com governanca.

## Arquitetura

- Canal primario: WhatsApp.
- Entrada real: backend recebe Evolution em `/api/v1/whatsapp/webhook`.
- Entrada n8n: webhook `POST /webhook/cordex-whatsapp-agent`, chamado apenas pelo backend com service token.
- Saida n8n: decisao estruturada para o backend: `send_reply`, `create_task`, `handoff` ou `no_reply`.
- Envio final: sempre pelo backend via `/api/v1/whatsapp/agent/reply` ou pelo retorno sincrono do webhook, nunca direto pela Evolution na V1.
- Agentes separados:
  - `01-whatsapp-internal-operator-agent`: equipe Cordex, tools operacionais e approval gates.
  - `02-whatsapp-external-service-agent`: leads/alunos, FAQ/RAG publico, triagem, handoff e resposta ao mesmo contato.
- Persistencia: Postgres para sessoes, mensagens, memoria, eventos WhatsApp, logs, aprovacoes, documentos e tarefas.
- RAG: pgvector com embeddings OpenAI.
- Estado padrao: workflows inativos ate revisao humana e credenciais reais.

Nota V1: os drafts importaveis usam policy/code nodes deterministicas para permitir teste sem credenciais reais. A camada AI Agent/OpenAI deve ser ligada dentro dos fluxos interno/externo quando as credenciais `Cordex OpenAI` e `Cordex Agent Postgres` forem configuradas, mantendo os mesmos contratos de entrada/saida.

## Arquivos

- `workflows/00-whatsapp-agent-router.json`: roteador WhatsApp-first.
- `workflows/01-whatsapp-internal-operator-agent.json`: agente interno da equipe Cordex.
- `workflows/02-whatsapp-external-service-agent.json`: agente externo controlado para leads/alunos.
- `workflows/03-whatsapp-send-reply.json`: prepara envio pelo backend.
- `workflows/01-tool-web-search.json`: pesquisa publica com fontes.
- `workflows/02-tool-email-assistant.json`: email, com envio/apagar/encaminhar pendentes de aprovacao.
- `workflows/03-tool-calendar-assistant.json`: agenda, com convidados/cancelamento pendentes de aprovacao.
- `workflows/04-tool-crm-assistant.json`: CRM/comercial.
- `workflows/05-tool-documents-rag.json`: RAG/documentos.
- `workflows/06-tool-database-query.json`: SQL seguro, SELECT por padrao.
- `workflows/07-tool-task-manager.json`: ferramenta funcional V1 de tarefas.
- `workflows/08-tool-whatsapp-communication.json`: politica de comunicacao WhatsApp, sem Telegram e sem broadcast.
- `workflows/09-human-approval-gateway.json`: aprovacao humana por WhatsApp.
- `workflows/10-agent-audit-logger.json`: auditoria.
- `workflows/11-tool-report-generator.json`: relatorios.
- `workflows/12-tool-n8n-workflow-manager.json`: gestao/auditoria de workflows n8n.
- `prompts/*.md`: system, roteador e validador.
- `sql/schema.sql`: schema Postgres.
- `.env.example`: variaveis esperadas.
- `SECURITY.md`: modelo de seguranca.
- `TEST_PLAN.md`: roteiro de validacao.

## Drafts n8n

Os drafts ficam inativos. IDs atuais:

| Arquivo | Workflow n8n | ID |
| --- | --- | --- |
| `00-whatsapp-agent-router.json` | Cordex WhatsApp AI Agent - Router | `8eApeMUW2PftRzld` |
| `01-whatsapp-internal-operator-agent.json` | Cordex WhatsApp AI Agent - Internal Operator Agent | `3706DcqiJJxZQA30` |
| `02-whatsapp-external-service-agent.json` | Cordex WhatsApp AI Agent - External Service Agent | `QRtfLjW8sgQq342D` |
| `03-whatsapp-send-reply.json` | Cordex WhatsApp AI Agent - Send Reply via Backend | `kvoELJVfVxKZPM3S` |
| `01-tool-web-search.json` | Cordex AI Agent - Tool Web Search | `cVbsWxhNBISLZchh` |
| `02-tool-email-assistant.json` | Cordex AI Agent - Tool Email Assistant | `TYrHlDuPOhMlTtpd` |
| `03-tool-calendar-assistant.json` | Cordex AI Agent - Tool Calendar Assistant | `EKWVDfDMcW5hyEy0` |
| `04-tool-crm-assistant.json` | Cordex AI Agent - Tool CRM Assistant | `c7Nez9PjrA0hl1ch` |
| `05-tool-documents-rag.json` | Cordex AI Agent - Tool Documents RAG | `ClH12En1nNA8oT7S` |
| `06-tool-database-query.json` | Cordex AI Agent - Tool Database Query | `lPBWb1nYP1YZrRIo` |
| `07-tool-task-manager.json` | Cordex AI Agent - Tool Task Manager | `fG603Ty3gyOngdj1` |
| `08-tool-whatsapp-communication.json` | Cordex WhatsApp AI Agent - Tool WhatsApp Communication Policy | `1Hf0Vz6ckBEe1NtN` |
| `09-human-approval-gateway.json` | Cordex AI Agent - Human Approval Gateway | `QL3C5XqSaF4GvL4t` |
| `10-agent-audit-logger.json` | Cordex AI Agent - Audit Logger | `xEPAG3ysMNxHgGCi` |
| `11-tool-report-generator.json` | Cordex AI Agent - Tool Report Generator | `8Qd32ytEOtXDktKM` |
| `12-tool-n8n-workflow-manager.json` | Cordex AI Agent - Tool n8n Workflow Manager | `iyytz6nFPaW8pKZH` |

## Instalacao

1. Aplique `sql/schema.sql` no Postgres usado pelo agente.
2. Configure as variaveis em `.env.example` no n8n e no backend.
3. Crie credenciais n8n:
   - `Cordex OpenAI`
   - `Cordex Agent Postgres`
   - `Cordex Backend Agent Service`
   - credenciais opcionais de Gmail, Calendar, CRM e sistemas internos.
4. Proteja o webhook `cordex-whatsapp-agent` com Header Auth ou reverse proxy confiavel.
5. Importe os JSONs de `workflows/` ou use os drafts criados.
6. Mantenha todos os workflows inativos durante a configuracao.
7. Configure no backend:
   - `N8N_WHATSAPP_AGENT_WEBHOOK_URL`
   - `CORDEX_AGENT_SERVICE_TOKEN`
   - `WHATSAPP_AGENT_MODE=sandbox`
   - `WHATSAPP_INTERNAL_ALLOWED_PHONES`
8. Execute os testes em `TEST_PLAN.md`.
9. Ative `WHATSAPP_AGENT_MODE=active` somente apos UAT.

## Fluxo de runtime

1. Evolution chama o backend em `/api/v1/whatsapp/webhook`.
2. Backend ignora grupos, `fromMe`, instancias desconhecidas e payload sem telefone/texto.
3. Backend registra inbound, resolve tenant, membro/lead/sequencia e classifica `internal | external`.
4. Backend chama o webhook n8n com payload normalizado.
5. n8n deduplica por `event_id`/`provider_message_id`, aplica politicas e escolhe rota.
6. n8n retorna decisao ao backend.
7. Backend envia pelo provedor oficial apenas quando a decisao for `send_reply` ou `handoff`, o destinatario for o mesmo remetente e `WHATSAPP_AGENT_MODE=active`.
8. Se n8n falhar e `WHATSAPP_AGENT_FALLBACK_TO_LEGACY_NURTURING=true`, backend usa o fluxo legado sem duplicar resposta.

## Payload backend -> n8n

```json
{
  "event_id": "string",
  "provider_message_id": "string",
  "gym_id": "string",
  "instance": "string",
  "sender_phone": "string",
  "sender_name": "string",
  "audience": "internal | external",
  "message": "string",
  "attachments": [],
  "timestamp": "string",
  "source": "evolution",
  "context": {
    "member_id": "string | null",
    "lead_id": "string | null",
    "sequence_id": "string | null",
    "role": "OWNER | MANAGER | OPERATOR | VIEWER | null"
  }
}
```

Exemplo:

```bash
curl -X POST "$N8N_BASE_URL/webhook/cordex-whatsapp-agent" \
  -H "Content-Type: application/json" \
  -H "X-Cordex-Agent-Token: replace_with_service_token" \
  -d '{
    "event_id": "msg-123",
    "provider_message_id": "wamid.123",
    "gym_id": "gym_123",
    "instance": "cordex-gym-123",
    "sender_phone": "5511999999999",
    "sender_name": "Ana",
    "audience": "external",
    "message": "Quais planos voces tem?",
    "attachments": [],
    "timestamp": "2026-05-24T12:00:00Z",
    "source": "evolution",
    "context": {
      "member_id": null,
      "lead_id": "lead_123",
      "sequence_id": null,
      "role": null
    }
  }'
```

## Retorno n8n -> backend

```json
{
  "event_id": "string",
  "status": "success | pending_approval | error | needs_clarification | no_reply",
  "action": "send_reply | create_task | handoff | no_reply",
  "recipient_phone": "string",
  "message": "string",
  "risk": "low | medium | high | critical",
  "approval_required": false,
  "metadata": {}
}
```

## Regras internas

- Numeros em `WHATSAPP_INTERNAL_ALLOWED_PHONES` entram como `internal`.
- Baixo risco pode responder automaticamente.
- Medio risco executa apenas dentro da role permitida.
- Alto risco e critico retornam `pending_approval`.
- OWNER/MANAGER aprovam acoes sensiveis por WhatsApp.
- Pode usar tools de tarefas, CRM, RAG, report, DB safe query, workflow audit e web search.

## Regras externas

- Responde somente ao mesmo `sender_phone`.
- Pode responder FAQ seguro, consultar RAG publico/controlado, registrar interesse e criar handoff.
- Nao pode rodar SQL, alterar workflow, enviar para terceiros, acessar dados sensiveis ou fazer broadcast.
- Pedidos sobre cobranca, contrato, cancelamento, senha, token, dados sensiveis, producao ou acao destrutiva viram `handoff`.

## Contratos das tools

### 1. Web Search / Research
Entrada:
```json
{ "query": "string", "depth": "basic | deep", "output_format": "summary | report | table | action_plan" }
```
Saida:
```json
{ "status": "success | error", "summary": "string", "sources": [], "recommendations": [] }
```

### 2. Email Assistant
Entrada:
```json
{
  "action": "search_emails | summarize_thread | draft_reply | send_email | classify_email | extract_tasks",
  "query": "string",
  "recipient": "string",
  "subject": "string",
  "body": "string"
}
```
Saida:
```json
{ "status": "success | pending_approval | error", "result": {}, "approval_required": true }
```

### 3. Calendar Assistant
Entrada:
```json
{
  "action": "check_availability | create_event | reschedule_event | cancel_event",
  "date_range": {},
  "attendees": [],
  "title": "string",
  "description": "string"
}
```
Saida:
```json
{ "status": "success | pending_approval | error", "event": {} }
```

### 4. CRM / Comercial
Entrada:
```json
{ "action": "string", "lead_name": "string", "company": "string", "stage": "string", "notes": "string" }
```
Saida:
```json
{ "status": "success | error", "lead": {}, "next_steps": [] }
```

### 5. RAG / Documentos
Entrada:
```json
{ "question": "string", "collection": "string", "top_k": 5 }
```
Saida:
```json
{ "status": "success | error", "answer": "string", "citations": [], "confidence": "low | medium | high" }
```

### 6. Database Query
Entrada:
```json
{ "intent": "string", "sql": "string", "parameters": {} }
```
Saida:
```json
{ "status": "success | pending_approval | error", "rows": [], "summary": "string" }
```

### 7. Task Manager
Entrada:
```json
{
  "action": "create_task | update_task | list_tasks | complete_task",
  "title": "string",
  "description": "string",
  "assignee": "string",
  "due_date": "string",
  "priority": "low | medium | high | urgent"
}
```
Saida:
```json
{ "status": "success | error", "task": {} }
```

### 8. WhatsApp Communication Policy
Entrada:
```json
{ "action": "draft_message | send_message | summarize_conversation", "recipient": "string", "message": "string" }
```
Saida:
```json
{ "status": "success | pending_approval | error", "result": {}, "approval_required": true }
```

### 9. Report Generator
Entrada:
```json
{ "report_type": "commercial | operational | financial | technical | executive", "period": "string", "data_sources": [], "format": "markdown | html | pdf | spreadsheet" }
```
Saida:
```json
{ "status": "success | error", "report": "string", "files": [] }
```

### 10. n8n Workflow Manager
Entrada:
```json
{ "action": "document_workflow | create_workflow | audit_workflow | activate_workflow | deactivate_workflow", "workflow_id": "string", "description": "string" }
```
Saida:
```json
{ "status": "success | pending_approval | error", "result": {} }
```

## Guia para adicionar nova ferramenta

1. Crie um workflow com `Execute Workflow Trigger`.
2. Defina contrato JSON de entrada e saida.
3. Valide payload no primeiro node.
4. Classifique risco por acao.
5. Use `09-human-approval-gateway` para alto risco.
6. Use `10-agent-audit-logger` para auditoria.
7. Adicione politica em `agent_tool_policies`.
8. Conecte ao agente interno ou externo, conforme audiencia.
9. Atualize prompts, README, SECURITY e TEST_PLAN.
10. Teste em sandbox antes de ativar.

## Checklist final de producao

- [ ] `schema.sql` aplicado.
- [ ] `pgvector` ativo.
- [ ] Credenciais OpenAI, Postgres e Backend Agent Service criadas.
- [ ] Webhook n8n protegido.
- [ ] `CORDEX_AGENT_SERVICE_TOKEN` forte e igual no backend/n8n.
- [ ] `WHATSAPP_AGENT_MODE=sandbox` validado antes de `active`.
- [ ] Numeros internos revisados em `WHATSAPP_INTERNAL_ALLOWED_PHONES`.
- [ ] Auto-reply externo revisado com FAQ/RAG publico.
- [ ] Fallback legado validado sem duplicidade.
- [ ] Logs revisados sem segredos.
- [ ] DB Query testado com allowlist.
- [ ] Broadcast bloqueado.
- [ ] Approval gateway testado para aprovar e negar.
- [ ] Ativacao aprovada por OWNER.
