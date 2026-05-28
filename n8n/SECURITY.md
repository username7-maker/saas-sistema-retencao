# Cordex WhatsApp AI Agent V1 - Seguranca

## Principios

- WhatsApp e o canal primario desta V1.
- O backend e o unico dono do webhook Evolution API e do envio final.
- O n8n nunca envia direto pela Evolution na V1.
- Nunca hardcodar credenciais, tokens, senhas ou dados sensiveis.
- Toda decisao do agente deve ser rastreavel por `event_id` e `provider_message_id`.
- Usuarios sem role conhecida sao `VIEWER`.
- Producao comeca em sandbox e so passa para active apos UAT e aprovacao de OWNER.

## Fronteiras de confianca

- Evolution -> backend: protegido por `WHATSAPP_WEBHOOK_TOKEN`.
- Backend -> n8n: protegido por `CORDEX_AGENT_SERVICE_TOKEN` e webhook n8n com Header Auth/reverse proxy.
- n8n -> backend reply: protegido por `CORDEX_AGENT_SERVICE_TOKEN`.
- n8n -> ferramentas externas: sempre por n8n Credentials ou ENV.

## Perfis

- `OWNER`: administra ferramentas e politicas; acoes criticas ainda exigem confirmacao explicita.
- `MANAGER`: consulta dados, cria tarefas, atualiza CRM e gera relatorios; nao apaga dados nem altera producao.
- `OPERATOR`: consulta, cria tarefas e gera rascunhos; nao envia mensagens externas sem aprovacao.
- `VIEWER`: apenas consulta e resumo.

## Classificacao de risco

- Baixo: FAQ seguro, resumo, organizacao, rascunho, triagem.
- Medio: criar tarefa, criar handoff, atualizar CRM nao destrutivo, consultar banco allowlisted.
- Alto: enviar mensagem externa, enviar email, criar evento com terceiros, alterar dados externos.
- Critico: apagar dados, broadcast, movimentar dinheiro, alterar producao, acessar dados sensiveis sem necessidade legitima.

## Politica interna

- Numeros em `WHATSAPP_INTERNAL_ALLOWED_PHONES` podem entrar no agente operacional.
- Baixo risco pode responder automaticamente.
- Medio risco exige role compativel.
- Alto risco retorna `pending_approval`.
- Critico bloqueia ou exige aprovacao explicita de OWNER.

## Politica externa

- O agente externo so pode responder ao mesmo `sender_phone`.
- Nao pode enviar para terceiros.
- Nao pode fazer broadcast.
- Nao pode rodar SQL.
- Nao pode alterar workflows.
- Nao pode acessar dados sensiveis.
- Pedidos sobre senha, token, contrato, cancelamento, cobranca, juridico, dados sensiveis, producao ou acao destrutiva devem virar `handoff`.

## Approval gate

O workflow `09-human-approval-gateway.json` deve:

- registrar solicitacao em `agent_approvals`;
- enviar resumo por WhatsApp para OWNER/MANAGER configurado;
- mostrar acao, ferramenta, payload redigido, risco e solicitante;
- receber decisao por webhook assinado;
- registrar aprovador e horario;
- retornar `approved`, `denied` ou `expired`.

## Banco de dados

- `06-tool-database-query` permite apenas `SELECT` por padrao.
- Queries devem ser parametrizadas.
- Tabelas devem estar em `ALLOWED_DB_TABLES`.
- `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE` e multiplas instrucoes devem ser bloqueadas ou exigir aprovacao.
- Nunca retornar segredos, hashes, tokens ou PII desnecessaria.
- `agent_whatsapp_events` deve ser usado para dedupe e auditoria de eventos inbound/outbound.

## Logs

Registrar:

- timestamp;
- event_id;
- provider_message_id;
- gym_id;
- audience;
- sender_phone redigido quando possivel;
- intencao;
- ferramenta;
- payload redigido;
- resultado;
- status;
- erro;
- approval_required;
- approved_by.

Nao registrar:

- tokens;
- senhas;
- headers de autenticacao;
- dados bancarios;
- anexos brutos sensiveis;
- conteudo completo de terceiros quando houver segredo ou PII desnecessaria.

## Modo sandbox

Enquanto `WHATSAPP_AGENT_MODE=sandbox`:

- o backend chama o n8n e registra a decisao;
- o backend nao envia mensagens reais do agente;
- a resposta legada pode assumir se o n8n falhar e o fallback estiver ligado;
- acoes sensiveis continuam como `pending_approval`;
- nenhum workflow deve ser ativado automaticamente.

## Checklist de seguranca

- [ ] Webhook Evolution protegido.
- [ ] Webhook n8n protegido.
- [ ] Service token forte e sem log.
- [ ] Credenciais somente via n8n Credentials/ENV.
- [ ] Logs sem segredo.
- [ ] RBAC populado em `agent_user_roles`.
- [ ] Politicas populadas em `agent_tool_policies`.
- [ ] Dedupe ativo por `event_id`.
- [ ] Fallback legado testado sem duplicidade.
- [ ] Approval gateway testado.
- [ ] Broadcast bloqueado.
- [ ] SQL destrutivo bloqueado.
- [ ] RAG externo separado de RAG interno.
- [ ] Workflows inativos ate aprovacao.
