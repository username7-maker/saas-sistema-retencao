# Phase 1 Context

## Objective

Eliminar o ultimo risco serio de perda de contexto comercial no CRM e remover o falso compartilhamento local de notas internas no `Profile 360`.

## Locked Decisions

- `Lead.notes` continua sendo a timeline canonica de eventos do lead.
- O drawer de lead nao sobrescreve mais `notes` durante edicao normal.
- Novas observacoes entram por append explicito via endpoint de notas.
- A leitura do frontend aceita entradas legadas `string`, `{ note }` e estruturadas.
- Notas internas do `Profile 360` passam a ser API-only; nada e lido de `localStorage`.

## Out of Scope

- Migracao destrutiva de historico legado de CRM.
- Timeline comercial separada em banco proprio.
- Redesenho completo do `Profile 360`.
