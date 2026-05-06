# Plano

1. Registrar fase GSD, Spec Kit e Obsidian.
2. Estender settings Kommo com canal principal, fallback e auto-close.
3. Criar roteador de canal de comunicação.
4. Evoluir Kommo para canal operacional da Work Queue.
5. Criar webhook Kommo com registro de evento e resolver seguro.
6. Atualizar contratos e UI da Work Queue/Settings.
7. Cobrir testes focados de settings, roteamento, Work Queue e webhook.

## Critério de aceite

- Academia com `primary_message_channel=kommo` vê CTAs Kommo na fila.
- `send-and-wait` cria handoff Kommo e deixa task aguardando resposta.
- Falha Kommo cai para WhatsApp.
- Webhook Kommo fecha task simples e escala mensagem sensível.
