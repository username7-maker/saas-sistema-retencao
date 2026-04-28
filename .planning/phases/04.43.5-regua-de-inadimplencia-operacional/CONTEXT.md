# 04.43.5 - Regua de Inadimplencia Operacional

## Contexto

A fase vem depois da unificacao Tasks + Work Queue e da maturidade operacional de tasks. O sistema ja possui `financial_entries`, `Task`, `TaskEvent` e modo execucao. A lacuna era transformar inadimplencia em rotina executavel, sem depender de dashboard ou memoria manual da equipe.

## Decisao De Produto

Inadimplencia V1 e assistida e auditavel:

- sem cobranca automatica;
- sem PIX/cartao/link gerado pelo sistema;
- sem envio autonomo;
- uma task aberta por aluno inadimplente;
- financeiro alimenta execucao diaria via `/tasks`.

## Fonte

`financial_entries` e a fonte V1. Recebiveis `open` vencidos sao tratados como atraso operacional mesmo antes de mudarem para `overdue`.
