# Plan - Spec 056

## Scope

Entrega V1 local: formulario guiado, calculos backend, historico, PDF e regua tecnica. Sem dependencias externas.

## Build order

1. Criar testes RED para service backend, PDF, historico e UI.
2. Expandir `Assessment` e `Member` com campos compativeis e migration nullable.
3. Implementar service antropometrico com politica de medidas, calculo, snapshot e hash.
4. Adicionar APIs V1 protegidas por feature flag e idempotencia.
5. Projetar historico unificado em leitura, combinando `Assessment` e `BodyCompositionEvaluation`.
6. Criar PDF premium antropometrico sem cards vazios.
7. Implementar seletor de modo em Nova Avaliacao e formulario manual no registro.
8. Adicionar regua D+8, D+14, D+75, D+90 sem alterar helper da bioimpedancia.
9. Registrar GSD/Spec Kit e executar gates focados.

## Constraints

- `BodyCompositionEvaluation` nao sera alterado.
- O modo `Com bioimpedancia` apenas abre o fluxo legado.
- Actuar fica fora da V1.
- Massa muscular permanece indisponivel.
- Nenhum registro historico sera recalculado.

## Rollout

- Feature flag: `anthropometric_assessment_v1`.
- Ativacao segura por academia/ambiente conforme configuracao existente.
- Falha em PDF ou regua nao deve apagar a avaliacao local ja persistida.

## Risk controls

- Testes de caracterizacao para bioimpedancia.
- Idempotencia por chave em banco.
- Snapshot imutavel e hash reproduzivel.
- DTO de historico com badge e aviso de comparabilidade limitada.
- Migracao expand/backfill nullable para reduzir risco operacional.
