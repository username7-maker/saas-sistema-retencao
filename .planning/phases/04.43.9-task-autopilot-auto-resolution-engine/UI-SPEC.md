# UI Spec - 04.43.9 Task Autopilot

## Work Queue

- Mostrar badges operacionais: `Criada pelo Autopilot`, `Escalada apos automacao`, `Aguardando resposta`, `Auto-resolvida`, `Bloqueada por seguranca`.
- Adicionar CTA `Enviar e aguardar` em tasks humanas com telefone.
- Manter `Abrir WhatsApp` como acao manual simples.
- Nao adicionar tela complexa de automacao ao operador.

## Settings

- Aba `Autopilot` para owner/manager.
- Defaults seguros visiveis:
  - Autopilot off.
  - Auto-close on quando Autopilot estiver ativo.
  - Auto-send off.
  - horario permitido 08:00-20:00.
- Exibir metricas simples: actions, auto-resolvidas, escaladas e bloqueadas.

## Gestao

- Metricas devem apoiar rollout, nao virar tela central da recepcao.
- Explainability fica em timeline/autopilot metrics, nao na fila curta.
