# Cordex WhatsApp AI Agent V1 - Test Plan

## 1. Validacao estatica

- Rodar `specify check`.
- Validar parse JSON de todos os arquivos em `n8n/workflows`.
- Confirmar que todos os workflows tem `"active": false`.
- Procurar segredos hardcoded em `n8n`.
- Confirmar que nao ha referencias a Telegram no caminho principal.

## 2. Backend WhatsApp

- `MESSAGES_UPSERT` externo gera payload n8n normalizado.
- Numero em `WHATSAPP_INTERNAL_ALLOWED_PHONES` vira `audience=internal`.
- Grupo continua ignorado.
- `fromMe=true` continua ignorado.
- Payload sem telefone/texto continua ignorado.
- Instancia desconhecida continua ignorada no router publico.
- n8n indisponivel aciona fallback legado quando `WHATSAPP_AGENT_FALLBACK_TO_LEGACY_NURTURING=true`.
- Quando n8n responde `send_reply`, backend envia por `send_whatsapp_sync` somente em `WHATSAPP_AGENT_MODE=active`.
- Resposta para telefone diferente do inbound e bloqueada.

## 3. Banco

- Aplicar `sql/schema.sql` em banco de teste.
- Confirmar extensoes `pgcrypto` e `vector`.
- Confirmar tabelas obrigatorias.
- Confirmar `agent_whatsapp_events`.
- Confirmar seed inicial de `agent_tool_policies`.

## 4. Importacao n8n

- Importar todos os JSONs.
- Confirmar workflows importados como inativos.
- Configurar credenciais placeholder.
- Executar sub-workflows com pin data.
- Manter producao desativada ate UAT.

## 5. Router WhatsApp

Payload externo seguro:
```json
{
  "event_id": "msg-001",
  "provider_message_id": "wamid.001",
  "gym_id": "gym_1",
  "instance": "gym_instance",
  "sender_phone": "5511999999999",
  "sender_name": "Ana",
  "audience": "external",
  "message": "Quais planos voces tem?",
  "attachments": [],
  "timestamp": "2026-05-24T12:00:00Z",
  "source": "evolution",
  "context": { "member_id": null, "lead_id": "lead_1", "sequence_id": null, "role": null }
}
```

Aceite:

- retorna `status=success`;
- retorna `action=send_reply`;
- retorna `recipient_phone` igual ao remetente;
- retorna `risk=low`.

Payload externo sensivel:
```json
{
  "event_id": "msg-002",
  "provider_message_id": "wamid.002",
  "gym_id": "gym_1",
  "instance": "gym_instance",
  "sender_phone": "5511999999999",
  "sender_name": "Ana",
  "audience": "external",
  "message": "Quero cancelar meu contrato e falar sobre cobranca",
  "attachments": [],
  "timestamp": "2026-05-24T12:01:00Z",
  "source": "evolution",
  "context": { "member_id": "member_1", "lead_id": null, "sequence_id": null, "role": null }
}
```

Aceite:

- retorna `action=handoff`;
- nao consulta SQL;
- nao envia para terceiros;
- mensagem informa que a equipe assumira.

## 6. Agente interno

Payload:
```json
{
  "payload": {
    "event_id": "msg-int-001",
    "gym_id": "cordex",
    "instance": "cordex_ops",
    "sender_phone": "5511888888888",
    "audience": "internal",
    "message": "Crie uma tarefa para revisar leads quentes amanha",
    "context": { "role": "OPERATOR" }
  }
}
```

Aceite:

- baixo risco retorna `success`;
- acao sensivel retorna `pending_approval`;
- nao envia mensagem externa sem approval.

## 7. Task Manager

Payload:
```json
{
  "action": "create_task",
  "title": "Revisar leads quentes",
  "description": "Checar follow-ups pendentes",
  "assignee": "operacao",
  "due_date": "2026-05-25",
  "priority": "high"
}
```

Aceite:

- retorna `success`;
- retorna objeto `task`;
- em sandbox nao dispara efeito externo.

## 8. WhatsApp Communication Policy

Envio unico:
```json
{ "action": "send_message", "recipient": "5511999999999", "message": "Mensagem de teste" }
```

Broadcast proibido:
```json
{ "action": "send_message", "recipient": ["5511999999999", "5511888888888"], "message": "Teste" }
```

Aceite:

- envio unico retorna `pending_approval`;
- broadcast retorna `error`;
- Telegram nao aparece como opcao.

## 9. Approval gateway

Solicitacao:
```json
{
  "tool_name": "whatsapp_communication",
  "risk": "high",
  "requested_by": "operator_1",
  "payload": {
    "action": "send_message",
    "recipient": "5511999999999",
    "message": "Teste"
  }
}
```

Decisao:
```json
{
  "approval_id": "approval_test",
  "status": "approved",
  "approved_by": "owner_1",
  "reason": "UAT aprovado"
}
```

Aceite:

- aprovado e negado retornam status distintos;
- decisao e registrada quando Postgres estiver conectado.

## 10. Database Query

Permitido:
```json
{ "intent": "listar tarefas abertas", "sql": "SELECT id, title FROM agent_tasks WHERE status = $1", "parameters": { "status": "open" } }
```

Bloqueados:
```json
{ "intent": "apagar", "sql": "DELETE FROM agent_tasks", "parameters": {} }
```
```json
{ "intent": "multi", "sql": "SELECT * FROM agent_tasks; DROP TABLE agent_tasks", "parameters": {} }
```

Aceite:

- SELECT simples passa por validacao.
- DELETE/multiplas instrucoes retornam `pending_approval` ou bloqueio.

## 11. RAG

Payload sem documentos:
```json
{ "question": "Qual e a politica publica de planos?", "collection": "cordex-public", "top_k": 5 }
```

Aceite:

- retorna baixa confianca quando nao houver evidencia;
- nao inventa conteudo;
- separa RAG publico de interno.

## 12. Relatorio final de UAT

Registrar:

- data/hora;
- workflow testado;
- payload usado;
- resultado;
- falha encontrada;
- decisao de aprovacao.
