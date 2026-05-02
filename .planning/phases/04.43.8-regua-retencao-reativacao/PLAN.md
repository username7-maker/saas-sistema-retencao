# Plan - 04.43.8 Regua Retencao e Reativacao

## Objetivo

Separar a operacao de retencao por estagio de inatividade para reduzir ruido da fila diaria e orientar a equipe com playbooks corretos.

## Entregas

1. Criar dominio deterministico de estagios:
   - `monitoring`: 0-6 dias
   - `attention`: 7-13 dias
   - `recovery`: 14-29 dias
   - `reactivation`: 30-44 dias
   - `manager_escalation`: 45-59 dias
   - `cold_base`: 60+ dias
2. Estender payload de fila de retencao com label, prioridade, owner sugerido, lane e cooldown.
3. Atualizar playbooks por estagio.
4. Atualizar job diario de inteligencia de retencao para persistir `Member.retention_stage`.
5. Atualizar Work Queue e AI Inbox para nao deixar `cold_base` dominar a operacao diaria.
6. Atualizar Dashboard de Retencao com lanes e filtro de estagio.
7. Criar testes focados de dominio e contrato.

## Validacao

- Backend: regras de dias, contrato da fila, filtro por estagio e Work Queue.
- Frontend: build TypeScript e renderizacao das lanes.
- Piloto: validar lista real de alunos 30+ com recepcao/professores/gestao.
