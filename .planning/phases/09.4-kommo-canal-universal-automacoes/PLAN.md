# Plano

1. Criar acao semantica `send_primary_channel` para Autopilot.
2. Atualizar policies de retencao/financeiro para nao hard-codear WhatsApp.
3. Atualizar executor do Autopilot para resolver Kommo/WhatsApp/manual via `communication_channel_service`.
4. Atualizar automacoes legadas: `send_whatsapp` respeita canal principal; `send_to_kommo` usa Salesbot quando possivel.
5. Expor cobertura das rotas Kommo por dominio em settings.
6. Ajustar UI de Settings > Kommo para mostrar o que esta pronto ou faltando.
7. Validar com testes focados e build.
