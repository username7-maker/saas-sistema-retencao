# Spec 019 - BI Foundation Upgrade

## User Story

Como gestor da academia, quero uma base de BI que conecte receita, retencao, onboarding, execucao da equipe e Autopilot para saber onde agir primeiro.

## Functional Requirements

- `GET /api/v1/dashboards/bi-foundation` deve continuar retornando cohort, LTV, forecast, receita em risco e impacto de follow-up.
- O mesmo endpoint deve incluir `onboarding_activation`.
- O mesmo endpoint deve incluir `retention_stage_mix`.
- O mesmo endpoint deve incluir `staff_execution`.
- O mesmo endpoint deve incluir `ai_first_ops`.
- O mesmo endpoint deve incluir `manager_actions`.
- Bioimpedancia deve contar como avaliacao realizada na leitura de ativacao.
- Quando a base de Autopilot, onboarding ou follow-up estiver vazia, o endpoint deve retornar flags honestas de qualidade.
- A UI deve mostrar os novos dados de forma compacta em Dashboard e Relatorios.

## Non-Goals

- Novo banco analitico.
- Nova rota de BI paralela.
- Exportacao PDF nova nesta fase.
- Metricas editaveis por usuario.

## Acceptance Criteria

- Payload antigo continua compativel.
- Dashboard executivo mostra execucao, onboarding, Autopilot e acoes de gestao.
- Reports mostram a Base de BI expandida.
- Testes backend e frontend focados passam.
