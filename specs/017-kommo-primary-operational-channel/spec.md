# Spec 017 - Kommo Primary Operational Channel

## User Story

Como gestor da academia, quero que a equipe execute comunicação operacional pela Kommo, mantendo o Cordex Gym OS como cérebro de prioridade, contexto, mensagem pronta e registro de resultado.

## Requirements

- Kommo deve poder ser o canal principal por academia.
- Work Queue deve criar handoff Kommo com mensagem pronta e contexto.
- WhatsApp deve continuar como fallback.
- Webhook Kommo deve registrar eventos e permitir auto-fechamento seguro.
- Mensagens sensíveis devem escalar para humano.

## Non-goals

- Envio autônomo pela Kommo.
- Editor visual de canais.
- Substituir Work Queue.
