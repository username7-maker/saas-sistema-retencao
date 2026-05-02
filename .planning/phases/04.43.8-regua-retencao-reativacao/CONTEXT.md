# Context - 04.43.8 Regua Retencao e Reativacao

## Problema

O dashboard de retencao tratava alunos com 7 dias e 60 dias sem check-in como a mesma fila operacional. Isso gerava uma lista grande, com muitos alunos de 30+ dias aparecendo como alto risco, mas sem diferenciar prevencao, recuperacao, reativacao, escalacao gerencial e base fria.

## Decisao

Risco e prioridade operacional deixam de ser a mesma coisa:

- `risk_score` continua medindo risco.
- `retention_stage_priority` define urgencia e lane de operacao.
- `30+` dias sem check-in e reativacao, nao lembrete simples.
- `60+` dias vira base fria e sai da fila diaria padrao.

## Dados usados

- `Member.last_checkin_at`
- `Member.join_date`
- `Member.retention_stage`
- `RiskAlert`
- `Task`
- `TaskEvent`
- Work Queue
- AI Inbox
- Dashboard de Retencao

## Fora de escopo

- Envio automatico de WhatsApp, Kommo ou e-mail.
- Nova tabela de retencao.
- Campanhas completas de winback.
- Backfill completo de historico antigo.
