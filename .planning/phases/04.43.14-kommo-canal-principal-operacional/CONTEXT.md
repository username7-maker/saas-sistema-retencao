# Contexto

## Problema

A academia vai operar comunicação principalmente pela Kommo. O AI Gym OS já cria handoffs pontuais, mas Tasks, Work Queue, Retenção, AI Inbox e Autopilot ainda assumem WhatsApp como canal padrão.

## Decisão

Kommo passa a ser canal operacional principal, com fallback WhatsApp. A V1 não envia mensagem automática pela Kommo; ela cria contexto, tarefa e mensagem pronta para o operador executar dentro da Kommo.

## Guardrails

- Sem envio autônomo pela Kommo nesta fase.
- Auto-fechamento permitido apenas com evento seguro recebido pela Kommo.
- Casos sensíveis escalam para humano.
- Fallback WhatsApp quando Kommo não estiver configurada ou falhar.
