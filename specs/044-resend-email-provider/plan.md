# Implementation Plan

1. Trocar `app.utils.email` de SendGrid SDK para Resend HTTP API via `httpx`.
2. Adicionar configuracoes `EMAIL_PROVIDER`, `RESEND_API_KEY`, `RESEND_SENDER`, `RESEND_REPLY_TO` e `EMAIL_TIMEOUT_SECONDS`.
3. Atualizar `forgot-password` para usar `settings.email_delivery_configured`.
4. Remover dependencia `sendgrid` dos requirements.
5. Atualizar testes de e-mail, auth router, config e dispatches com erros Resend.
6. Atualizar `.env.example` sem segredos reais.
7. Registrar validacao e observacao de seguranca sobre rotacao da chave exposta no chat.
