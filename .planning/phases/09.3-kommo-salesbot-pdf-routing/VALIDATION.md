# Validacao

## Manual
1. Configurar Kommo com URL, token e `primary_message_channel=kommo`.
2. Configurar rota `body_composition` com pipeline, etapa, salesbot, campo de mensagem e campo de PDF.
3. Abrir um aluno com telefone e bioimpedancia salva.
4. Clicar em `Enviar PDF via Kommo`.
5. Confirmar que o lead correto foi criado/atualizado na Kommo, no pipeline/etapa configurado.
6. Confirmar que o Salesbot rodou e a mensagem/PDF chegou ao numero do aluno.
7. Responder pela Kommo e verificar webhook/autofechamento.

## Casos de Erro
- Sem telefone: erro claro.
- Sem rota: erro claro e fallback `Preparar na Kommo`.
- Sem `PUBLIC_BACKEND_URL`: erro claro para PDF.
- Sem campo PDF: erro claro sem marcar como enviado.
- Salesbot falha: `MessageLog failed` e evento de falha.
