# Implementation Plan: Durable Jobs Closeout

**Feature**: [spec.md](./spec.md)  
**Phase Anchor**: `4.38 - Resiliencia de consultas, jobs e DoS logico`  
**Created**: 2026-04-16
**Status**: Completed, validated with accepted controlled operational sample

## Plan Intent

Fechar o delta restante da `4.38` sem abrir nova arquitetura: tornar uniforme o uso de `CoreAsyncJob` para os jobs criticos do piloto, expor observabilidade suficiente para budget operacional e remover o ultimo job opaco do fluxo de WhatsApp.

## Scope

### In scope

- `daily_nps_dispatch_job()` passa a apenas enfileirar `nps_dispatch`
- `monthly_reports_job()` passa a apenas enfileirar `monthly_reports_dispatch`
- serializacao de `CoreAsyncJob` passa a expor `queue_wait_seconds`
- transicoes de `CoreAsyncJob` ganham telemetria estruturada minima
- `/whatsapp/connect` devolve `job_id` e `job_status` do webhook setup quando aplicavel
- nova rota de status para `whatsapp_webhook_setup`
- regressao automatizada para scheduler, status e serializacao

### Out of scope

- broker novo
- fila distribuida externa
- redesign do scheduler inteiro
- UI nova de monitoramento
- qualquer expansao lateral fora do close-out da `4.38`

## Backend Slices

1. Ajustar serializacao/observabilidade de `CoreAsyncJob`.
2. Migrar scheduler automatico de NPS e relatorios mensais para enfileirar jobs duraveis por tenant.
3. Expor status de `whatsapp_webhook_setup` e devolver `job_id` no `connect`.
4. Validar deduplicacao, escopo por tenant e regressao do contrato.

## Validation Plan

- `test_core_async_job_service.py`
- `test_scheduler_jobs.py`
- `test_nps_router.py`
- `test_reports_router.py`
- `test_whatsapp_router.py`
- `specify check`

## Exit Condition

O corte pode marcar `4.38 execute` como fortalecido quando:

- `nps_dispatch` e `monthly_reports_dispatch` automaticos passarem pelo envelope duravel
- `queue_wait_seconds` estiver observavel
- `whatsapp_webhook_setup` deixar de ser job opaco
- a regressao focada estiver verde

## Closure

- `daily_nps_dispatch_job()` e `monthly_reports_job()` passaram a enfileirar `CoreAsyncJob`
- `queue_wait_seconds` ficou observavel
- `whatsapp_webhook_setup` deixou de ser job opaco
- a regressao focada ficou verde
- a fase foi validada com amostra operacional minima controlada aceita:
  - `1` `CoreAsyncJob`
  - `job_type = whatsapp_webhook_setup`
  - `p95 queue_wait_seconds = 7.21s`
