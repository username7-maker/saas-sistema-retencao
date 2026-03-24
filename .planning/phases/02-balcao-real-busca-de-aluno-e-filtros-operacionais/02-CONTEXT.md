# Phase 2 Context

## Objective

Deixar recepcao e gerencia acharem o aluno certo com menos atrito usando a tela atual de membros.

## Locked Decisions

- A busca passa a cobrir `nome`, `email` e `extra_data.external_id`.
- A UI expoe presets fixos `7`, `14` e `30` dias sem check-in.
- A UI expoe filtro tri-state de provisorios.
- A listagem mostra badge de matricula/ID externo e badge de membro provisiorio.

## Explicit Limits

- Nao incluir busca por telefone/CPF nesta fase.
- Nao criar endpoint novo; reusar query params ja suportados.
