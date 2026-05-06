# Plano

## Backend

1. Corrigir score para contar apenas tasks de onboarding esperadas até hoje.
2. Limitar avaliação, NPS, WhatsApp inbound e resposta do aluno à janela D0-D30.
3. Corrigir handoff D30 para rodar até D37 sem duplicar.
4. Criar endpoint `GET /api/v1/onboarding/cockpit`.
5. Adicionar deduplicação por etapa do onboarding e arquivamento operacional de duplicatas.
6. Garantir `work_queue_visible_from` nas tasks futuras.
7. Permitir `TRAINER` no score detalhado.
8. Usar Autopilot apenas para auto-fechamento por check-in, avaliação e resposta WhatsApp.

## Frontend

1. Consumir o cockpit agregado.
2. Mostrar fase atual, próxima ação e responsável sugerido.
3. Manter jornada completa visível, mas sem poluir o `Fazer agora`.
4. Exibir métricas D0-D30 de forma simples.

## Validação

1. Score D1 não penaliza D7/D15/D30.
2. Tasks futuras não aparecem em `do_now`.
3. Cockpit retorna dados tenant-scoped.
4. Trainer acessa score detalhado.
5. Auto-fechamento não fecha casos sensíveis como sucesso.
