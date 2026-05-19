# Validacao

## Backend
- Retencao elegivel gera metadata `retention_copy_agent_v1`.
- Onboarding gera metadata `onboarding_copy_agent_v1`.
- Task manual gera metadata `task_copy_agent_v1`.
- Caso sensivel bloqueia IA e preserva template.
- Falha de OpenAI cai para fallback.

## Frontend
- Work Queue exibe badges de origem.
- Regenerar rascunho atualiza item selecionado.
- Botoes de envio/copia usam o texto efetivo.

## Manual
1. Abrir `/tasks`.
2. Selecionar task de retencao.
3. Conferir badge de mensagem.
4. Clicar `Regenerar rascunho`.
5. Copiar/enviar por canal principal com supervisao humana.
