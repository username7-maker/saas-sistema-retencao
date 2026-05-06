# Spec 014 - Onboarding Cockpit e Jornada Inteligente

## User Story

Como gestor, recepção ou professor, quero ver o onboarding como uma jornada D0-D30 clara, para saber qual aluno precisa de ação agora sem ser confundido por tasks futuras.

## Requisitos Funcionais

- RF1: O sistema mantém etapas D0/D1/D3/D7/D15/D30.
- RF2: Tasks futuras não aparecem no `Fazer agora` antes de `work_queue_visible_from`.
- RF3: O score de tasks considera apenas etapas esperadas até hoje.
- RF4: Avaliação, NPS e resposta contam apenas na janela D0-D30 ou quando ligados ao onboarding.
- RF5: Handoff D30 processa D30-D37 sem duplicidade.
- RF6: `TRAINER` pode acessar score detalhado sem dados sensíveis adicionais.
- RF7: `/api/v1/onboarding/cockpit` retorna resumo, membros, críticos, distribuição, tasks por etapa e métricas.
- RF8: Duplicatas antigas são arquivadas operacionalmente, não deletadas.
- RF9: Autopilot pode auto-fechar etapas compatíveis por evidência real, sem envio automático.

## Requisitos Não Funcionais

- RNF1: Todas as leituras são tenant-scoped por `gym_id`.
- RNF2: O endpoint cockpit evita N+1 crítico.
- RNF3: O fluxo antigo continua compatível.
- RNF4: Não há exclusão física de histórico.

## Critérios de Aceite

- Score D1 não penaliza D7/D15/D30.
- Tasks futuras aparecem na jornada e lista completa, não no `do_now`.
- Cockpit carrega com dados agregados.
- Trainer acessa score detalhado.
- Auto-fechamento não trata mensagem sensível como sucesso.
