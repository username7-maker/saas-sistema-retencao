# Spec 034 - Kommo Universal Automation Channel

## Goal
Toda automacao de comunicacao deve usar o canal principal da academia. Kommo deve ser usado quando configurado; WhatsApp e manual sao fallback explicitos.

## Requirements
- `send_primary_channel` como acao semantica.
- Policies novas nao devem hard-codear WhatsApp.
- Automacoes legadas devem respeitar `primary_message_channel`.
- Settings deve expor cobertura de rotas Kommo por dominio.
- Logs devem registrar canal solicitado, resolvido e fallback.
