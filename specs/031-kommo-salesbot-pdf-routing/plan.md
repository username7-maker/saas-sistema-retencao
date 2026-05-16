# Implementation Plan

1. Database: `kommo_domain_routes` e `kommo_member_domain_links`.
2. Backend services: rota Kommo, Salesbot runner e public PDF link.
3. API: settings rotas, generic send-message e body composition send-kommo.
4. Frontend: Settings route editor e botoes de bioimpedancia.
5. Tests: service-level tests para route missing, Salesbot success e PDF token.

## Technical Notes
- Salesbot run recebe apenas lead/entity; mensagem e PDF devem ser gravados em campos customizados do lead antes da execucao.
- "Abas" = pipeline/stage/tags.
- Se a Kommo nao aceitar anexo dinamico no canal, o campo PDF deve ser usado pelo Salesbot para enviar link temporario.
