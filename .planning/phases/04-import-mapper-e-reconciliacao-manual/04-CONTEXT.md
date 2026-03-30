# Phase 4 Context

## Objective

Permitir reconciliacao manual e visual de colunas antes da gravacao final das importacoes de alunos, check-ins e historico de avaliacoes.

## Locked Decisions

- O mapper atua sobre o preview/import existente; nao substitui o motor atual.
- O backend recebe `column_mapping` opcional e remapeia colunas para aliases canonicos antes da validacao.
- A UI exige revalidacao quando o mapping e alterado.
- Confirmacao final continua separada do preview.

## Out of Scope

- Reconciliacao linha a linha com merge manual de registros.
- Novo wizard de importacao em multiplas etapas.
- OCR ou heuristica pesada para planilhas ruins.
