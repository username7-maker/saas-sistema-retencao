# 04.43.12 - Perfil Operacional Inteligente

## Contexto

O Perfil 360 do aluno ja e uma das superficies mais ricas do AI Gym OS. Ele agrega cadastro, risco, check-ins, avaliacoes, bioimpedancia, metas, treino, restricoes, tasks, timeline, NPS, origem comercial, consentimentos e inteligencia operacional.

Hoje, porem, ele ainda funciona como um painel 360 fragmentado. O frontend monta a tela com varias chamadas independentes (`profile360`, membro, avaliacoes, evolucao, `summary360`, intelligence context, timeline, bioimpedancia e tasks) e a proxima melhor acao ainda vem principalmente da inteligencia de avaliacao.

O produto precisa evoluir o perfil para uma central de decisao operacional:

- quem e o aluno
- qual e o estado real agora
- por que ele esta nesse estado
- o que ja foi tentado
- qual e a proxima melhor acao global
- se o Autopilot pode resolver
- se precisa humano, quem deve agir
- como registrar e medir se resolveu

## Base real existente

- `Member` ja possui sinais operacionais relevantes: `preferred_shift`, `risk_score`, `risk_level`, `last_checkin_at`, `onboarding_score`, `onboarding_status`, `retention_stage`, `churn_type`, `is_vip` e `extra_data`.
- `member_intelligence_service` ja gera contexto canonico com consentimento, ciclo de vida, atividade, avaliacao, operacao, risco, sinais e qualidade de dados.
- `/api/v1/tasks` ja aceita `member_id`, mas o Perfil 360 ainda busca tasks amplas e filtra no frontend.
- `TaskEvent`, `AutopilotEvent`, `AutopilotAction` e `/api/v1/autopilot/timeline` ja existem e devem ser reaproveitados.
- `member_timeline_service` ja agrega parte da jornada, mas ainda nao inclui todos os eventos relevantes para uma decisao operacional completa.
- Notas internas do Perfil 360 ainda ficam em `member.extra_data`.

## Decisao de Produto

O perfil do aluno deve deixar de ser apenas uma tela de consulta e virar o cockpit de decisao do aluno.

Frase guia:

> O perfil do aluno nao deve apenas mostrar historico. Ele deve dizer o que fazer agora, por que, quem deve fazer e se o sistema pode resolver sozinho.

## Objetivo

Criar uma camada de perfil operacional unica e role-aware, com snapshot backend, next best action global, timeline ampliada e integracao com Autopilot.

## Fora de Escopo

- Envio automatico novo de WhatsApp.
- Criar novo motor paralelo de timeline ignorando `TaskEvent` e `Autopilot`.
- Reescrever toda a tela de Perfil 360 do zero.
- Criar app do aluno.
- Criar score medico ou conclusoes clinicas.
- Expor dados sensiveis para cargos que nao precisam deles.
