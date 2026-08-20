# Feature 044 - Resend Email Provider

## Summary

Substituir o envio operacional de e-mails do backend Cordex Gym OS para Resend, mantendo os contratos existentes de recuperacao de senha, convite de usuario, relatórios com anexo e automacoes que chamam `send_email_result`.

## Goals

- Usar Resend como provedor unico de e-mail transacional.
- Nao gravar chaves reais no repositorio.
- Manter `EmailSendResult` como contrato interno para minimizar impacto nos servicos.
- Preservar rollback quando convite/reset nao for realmente enviado.
- Classificar falhas operacionais do Resend com mensagens claras para o usuario.

## Requirements

- `RESEND_API_KEY` deve ser lida somente por variavel de ambiente.
- `RESEND_SENDER` define o remetente usado no payload do Resend.
- `RESEND_REPLY_TO` pode apontar para o e-mail operacional da Cordex.
- `onboarding@resend.dev` pode ser usado para teste enquanto `cordex.com` estiver sem DNS verificado.
- `noreply@cordex.com` so deve ser usado depois que DKIM/SPF/MX estiverem verificados no Resend.
- `SENDGRID_*` nao deve ser necessario para novos deploys.

## Acceptance Criteria

- Reset de senha chama Resend e so persiste token apos resposta 2xx.
- Convite para usuario definir senha chama Resend e faz rollback se envio falhar.
- Relatorios com anexo usam payload de attachments do Resend.
- Ausencia de `RESEND_API_KEY` retorna falha operacional clara.
- Erro de dominio/remetente nao verificado retorna `sender_identity_unverified`.
- Testes focados de auth, usuarios, e-mail e config passam.
