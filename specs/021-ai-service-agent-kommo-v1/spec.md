# Spec 021 - AI Service Agent Kommo V1

## User Story

Como recepcao ou gestor, quero que o Cordex Gym OS leia mensagens recebidas na Kommo, entenda o contexto do aluno/lead e prepare uma resposta segura para revisao humana, reduzindo tempo de atendimento sem perder controle operacional.

## Requirements

- Receber eventos Kommo de mensagem inbound com validacao de seguranca.
- Resolver aluno/lead pelo vinculo Kommo ou telefone.
- Usar contexto canonico do Cordex Gym OS antes de sugerir resposta.
- Classificar intencao, dominio, sensibilidade e dono recomendado.
- Gerar resposta sugerida curta e operacional.
- Criar handoff para Kommo/Work Queue sem autoenvio na V1.
- Bloquear e escalar casos sensiveis.
- Respeitar consentimento, opt-out, horario, cooldown e atividade humana recente.
- Registrar trilha em `AutopilotEvent`, `AutopilotAction` ou `TaskEvent`.
- Medir drafts, escalamentos, bloqueios e tempo de resposta.

## Non-goals

- Envio autonomo pela Kommo.
- Personal IA de treino.
- Corretor de movimento por video.
- Campanhas em massa.
- Negociacao financeira automatica.
- Resposta final a cancelamento, lesao, reclamacao ou contestacao.

## Success Criteria

- Pelo menos 50% das mensagens simples geram draft aproveitavel.
- 100% dos casos sensiveis testados escalam para humano.
- Nenhum draft e criado sem tenant/consentimento valido.
- Operador entende o resumo e a resposta em menos de 15 segundos.

