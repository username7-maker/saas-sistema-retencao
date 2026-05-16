# 09.3.1 - Kommo Native PDF Upload

## Contexto

A fase 09.3 colocou a Kommo como canal operacional real via Salesbot por dominio, usando `pdf_url` temporario em campo customizado. Para a ProGym, o requisito agora e mais forte: o PDF deve ser enviado/anexado nativamente na Kommo, nao apenas como link.

## Decisao

PDF nativo passa a ser o sucesso principal do fluxo Kommo. Link temporario permanece como fallback explicito quando a rota permitir.

## Estado Atual

- `KommoDomainRoute` guarda pipeline, etapa, Salesbot e campos de mensagem/PDF.
- `send_member_message_via_kommo_salesbot` cria/atualiza lead e executa Salesbot.
- Bioimpedancia chama `/send-kommo` e hoje envia `pdf_url`.

## Alvo

- Gerar PDF em bytes.
- Fazer upload pela Files API da Kommo.
- Anexar arquivo ao lead correto.
- Registrar metadados auditaveis.
- Acionar Salesbot depois do anexo.
- Exigir upload nativo no fluxo de bioimpedancia por padrao.
