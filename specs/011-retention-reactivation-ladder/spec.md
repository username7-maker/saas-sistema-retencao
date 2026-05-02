# Feature Spec: Retention Reactivation Ladder

## User Story

Como gestor de academia, quero separar alunos inativos por estagio operacional para que a equipe saiba quando prevenir, recuperar, reativar, escalar para gerente ou mover para base fria.

## Scope

### Included

- Calculo deterministico por dias sem check-in.
- Persistencia em `Member.retention_stage`.
- Filtro `retention_stage` na fila de retencao.
- Payload semantico com label, prioridade, owner sugerido, lane e cooldown.
- Playbook por estagio.
- Work Queue sem `cold_base` na fila diaria padrao.
- Dashboard de Retencao com lanes.

### Excluded

- Envio automatico.
- Campanhas completas.
- Nova tabela de retencao.
- Backfill historico completo.

## Requirements

### R1 - Stage Calculation

O sistema deve classificar:

- 0-6: `monitoring`
- 7-13: `attention`
- 14-29: `recovery`
- 30-44: `reactivation`
- 45-59: `manager_escalation`
- 60+: `cold_base`

### R2 - Queue Payload

Itens de retencao devem expor:

- `retention_stage`
- `retention_stage_label`
- `retention_stage_priority`
- `recommended_owner_role`
- `operational_lane`
- `cooldown_until`

### R3 - Operational Priority

`risk_score` mede risco, mas `retention_stage_priority` organiza a urgencia operacional.

### R4 - Cold Base

`cold_base` nao deve aparecer na Work Queue padrao, apenas por filtro explicito/campanha.

### R5 - No Automatic Sending

Nenhum canal externo e enviado automaticamente nesta V1.
