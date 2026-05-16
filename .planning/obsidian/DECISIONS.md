# Decisions

## 2026-05-15 - Kommo Salesbot por Dominio
Kommo usa `salesbot_outbound` para envio operacional real. "Abas" da Kommo serao pipeline/etapa/tag por dominio. `handoff_task` permanece como fallback legado quando rota, Salesbot ou PDF nao estiverem prontos.

## 2026-05-15 - PDF Kommo Nativo
PDF via Kommo deve ser upload/anexo nativo quando a rota exigir documento. `pdf_url` temporario permanece como fallback explicito, nao como sucesso principal da bioimpedancia.
