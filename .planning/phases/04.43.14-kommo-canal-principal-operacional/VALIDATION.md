# Validacao

## Cenários

- Settings salva Kommo como canal principal.
- Work Queue usa Kommo em `channel=auto`.
- Work Queue cai para WhatsApp quando Kommo falha.
- Webhook Kommo com resposta simples fecha task.
- Webhook Kommo com termo sensível escala para humano.
- Eventos respeitam `gym_id`.

## Evidencia executada

- Backend compila com novo router/service/schema.
- Testes focados de Work Queue e users passaram.
- Testes focados de Kommo settings e handoff legado passaram.
- Frontend build passou com os novos campos e controles.

## Validacao manual pendente no piloto

- Configurar `KOMMO_WEBHOOK_TOKEN`.
- Salvar `primary_message_channel=kommo` em Settings > Kommo.
- Executar uma task com `Enviar para Kommo` e confirmar criacao de tarefa na Kommo.
- Enviar uma resposta simples pela Kommo e confirmar auto-fechamento.
- Enviar uma resposta sensivel e confirmar escalonamento.
