# Spec 032 - Kommo Native PDF Upload

## Objetivo

Enviar PDFs pelo canal Kommo como arquivo nativo, anexado ao lead e usado pelo Salesbot, mantendo link temporario apenas como fallback explicito.

## Requisitos

- `body_composition` usa PDF nativo obrigatorio por padrao.
- O Cordex cria/usa lead por dominio antes do upload.
- Upload/anexo deve gerar metadados auditaveis.
- Se upload nativo falhar em modo obrigatorio, nao marcar envio como sucesso.
- Webhook Kommo continua tratando respostas.

## Fora de Escopo

- Envio automatico sem clique humano.
- Trocar o provedor WhatsApp direto.
- Remover fallback `handoff_task`.
