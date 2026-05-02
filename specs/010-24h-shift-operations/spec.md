# Feature Spec: Operacao 24h por Turno Real

## User Story

Como gestor de academia 24h, quero separar madrugada, manha, tarde e noite para que cada login veja a fila de alunos do seu turno e a operacao nao fique misturada.

## Scope

### Included

- Novo turno canonico `overnight`.
- Aliases em portugues para madrugada.
- Calculo de turno preferido por check-in.
- Filtros por madrugada em usuarios, membros, tasks, Work Queue, retencao, avaliacoes e CRM.
- Arquivamento operacional de tasks antigas sem perda de historico.
- Preview/aplicar de saneamento para owner/manager.

### Excluded

- Escala completa de colaboradores.
- Envio automatico de WhatsApp, Kommo ou e-mail.
- Delecao, cancelamento ou conclusao em massa de tasks antigas.

## Requirements

### R1 - Turnos

O sistema deve aceitar `overnight`, `morning`, `afternoon` e `evening` em filtros, usuarios e entidades com turno preferido.

### R2 - Check-ins

O calculo de turno preferido deve usar:

- 00-05: `overnight`
- 06-11: `morning`
- 12-17: `afternoon`
- 18-23: `evening`

### R3 - Work Queue

`shift=my_shift` deve usar `user.work_shift`, inclusive `overnight`. Managers/owners podem usar `shift=all`.

### R4 - Cleanup Operacional

Tasks antigas elegiveis devem ser arquivadas em `extra_data.operational_archive`, sem alterar `status`, sem deletar e sem cancelar.

### R5 - Protecoes

Nao arquivar inadimplencia, jornada ativa e onboarding D0-D30.

## Acceptance Criteria

- Usuario madrugada visualiza fila correta em `Meu turno`.
- Manager alterna para todos os turnos.
- Filtros exibem `Madrugada`.
- Preview de saneamento nao muda dados.
- Apply remove ruido da fila diaria e preserva historico.
