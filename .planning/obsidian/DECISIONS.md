# Decisions

## 2026-05-15 - Kommo Salesbot por Dominio
Kommo usa `salesbot_outbound` para envio operacional real. "Abas" da Kommo serao pipeline/etapa/tag por dominio. `handoff_task` permanece como fallback legado quando rota, Salesbot ou PDF nao estiverem prontos.

## 2026-05-15 - PDF Kommo Nativo
PDF via Kommo deve ser upload/anexo nativo quando a rota exigir documento. `pdf_url` temporario permanece como fallback explicito, nao como sucesso principal da bioimpedancia.

## 2026-05-19 - Copy Agent Supervisionado
Mensagens operacionais podem ser melhoradas por agente especialista (`gpt-5.4-mini`) em modo rascunho. Safety vence copywriting: sensiveis, VIP, opt-out e disputas ficam com humano/template seguro.
