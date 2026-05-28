# 09.4 - Kommo como Canal Universal das Automacoes

## Contexto
O sistema ja possui Kommo como canal principal em Work Queue, bioimpedancia e alguns envios manuais via Salesbot. Ainda existem automacoes legadas que chamam WhatsApp/e-mail diretamente, especialmente `AutomationRule.SEND_WHATSAPP`, policies do Autopilot com `send_whatsapp` e automacoes de risco.

## Objetivo
Fazer toda automacao de comunicacao resolver o canal pelo tenant. Se a academia usa Kommo como canal principal, o sistema tenta Kommo/Salesbot primeiro e registra fallback WhatsApp/manual de forma auditavel.

## Fora de escopo
- Remover WhatsApp direto.
- Trocar nomes tecnicos persistentes.
- Criar autoenvio sem safety checks.
- Configurar pipelines/Salesbots dentro da Kommo.
