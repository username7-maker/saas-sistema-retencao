# Plan

## Backend

- Criar `KommoFileAttachment` tenant-scoped.
- Criar migration `20260515_0045`.
- Criar `kommo_file_service` para descobrir `drive_url`, criar sessao, subir arquivo, extrair `file_uuid` e anexar ao lead.
- Estender rota Kommo com modo de PDF e campos de arquivo.
- Integrar o upload nativo ao `kommo_service`.
- Atualizar bioimpedancia para enviar PDF nativo por padrao.

## Frontend

- Mostrar modo de PDF em Settings > Kommo.
- Adicionar campos de `file_uuid`, nome do arquivo e nota/anexo.
- Renomear CTA para `Enviar PDF nativo via Kommo`.
- Mostrar estados de upload/anexo quando houver resposta.

## Validacao

- Testes de servico para upload nativo e fallback.
- Testes focados de settings e bioimpedancia Kommo.
- `specify check`, testes backend focados, lint/build frontend.
