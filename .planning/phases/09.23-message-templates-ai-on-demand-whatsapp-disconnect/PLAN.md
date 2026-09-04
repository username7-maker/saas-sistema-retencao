# Phase 09.23 - Mensagens prontas, IA sob demanda e WhatsApp bloqueado

## Objetivo

Eliminar chamadas generativas automáticas em comunicações operacionais, oferecer melhoria de texto somente após ação humana explícita e impedir qualquer disparo de WhatsApp até uma nova habilitação consciente.

## Escopo entregue

- Registro central de templates por domínio e canal, com fallback versionado em código.
- Overrides por academia, editáveis por owner/manager e restauráveis ao padrão.
- Preview determinístico com validação estrita de placeholders.
- Compositor `Melhorar com IA`, com comparação, aplicar e descartar.
- Política central que exige usuário, academia, objetivo, origem e idempotência para prompts de comunicação.
- Redação de e-mail, CPF e telefone antes do envio de contexto ao modelo.
- Auditoria por hash, tokens, duração, modelo, prompt e decisão do operador.
- Métricas agregadas do compositor por academia.
- Cache curto por usuário/contexto e proteção contra clique duplicado.
- Mensagens automáticas de retenção, onboarding, nutrição, objeções, briefing, comercial e agentes convertidas para conteúdo determinístico.
- OCR, avaliação física, análises técnicas e cálculos preservados fora desta política.
- Kill switch global `WHATSAPP_OUTBOUND_ENABLED` e controle por academia, ambos desligados por padrão.
- Verificação central dos dois gates em todos os caminhos de envio, inclusive worker, automações, documentos e agentes.
- `skipped`/`blocked` não avançam jornadas nem entram como envio confirmado.
- A conexão por QR nunca habilita disparos automaticamente.
- A referência da instância só é apagada após o provedor confirmar desconexão; falha mantém o vínculo visível e o envio bloqueado.

## Contratos

- `GET /api/v1/message-templates`
- `PUT /api/v1/message-templates/{template_key}`
- `DELETE /api/v1/message-templates/{template_key}/override`
- `POST /api/v1/message-templates/{template_key}/preview`
- `POST /api/v1/message-composer/improve`
- `POST /api/v1/message-composer/{request_id}/apply`
- `POST /api/v1/message-composer/{request_id}/discard`
- `GET /api/v1/message-composer/metrics`
- `PATCH /api/v1/whatsapp/outbound`

## Sequência segura de release

1. Manter o gate global falso na API e no worker.
2. Gerar dump lógico do banco ativo e registrar digest.
3. Aplicar a migração `20260904_0060`.
4. Publicar API e worker pelo mesmo commit.
5. Publicar frontend pelo mesmo commit.
6. Executar smoke sem destinatário real.
7. Consultar `connectionState`, tentar logout e remover apenas instâncias confirmadas como fechadas.
8. Manter histórico de mensagens e auditoria intactos.

## Rollback

- O gate global continua falso durante todo o rollout.
- Reverter API, worker e frontend ao deployment anterior se o smoke falhar.
- A migração é aditiva; não remover tabelas/colunas durante rollback de aplicação.
- Restaurar banco somente mediante incidente de dados confirmado.

