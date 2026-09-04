# Spec 055 - Comunicação determinística e IA sob demanda

## Invariantes

1. Abrir página, drawer, webhook, cron, worker ou criar tarefa não autoriza IA de comunicação.
2. Mensagens operacionais sempre possuem uma versão pronta determinística.
3. IA de comunicação exige ação humana explícita e nunca envia a mensagem.
4. Aplicar uma melhoria altera somente o rascunho da ação corrente.
5. Falha ou timeout conserva a mensagem-base.
6. OCR, cálculos e análises técnicas não são classificados como comunicação.
7. Nenhum disparo de WhatsApp ocorre se qualquer gate estiver desligado.
8. `blocked` e `skipped` nunca equivalem a `sent`.
9. Histórico e mensagens legadas não são reprocessados.
10. Credenciais/sessões só são removidas após confirmação do provedor.

## Critério de aceite

- Zero chamada de IA de comunicação sem `AiInvocationContext` explícito e completo.
- Preview, aplicar e descartar são auditáveis e idempotentes.
- Templates e overrides são isolados por academia e domínio de papel.
- API, worker e frontend expõem a mesma versão de release.
- WhatsApp permanece bloqueado após conexão por QR até habilitação separada do owner.

