# Spec 053 - Daily Commercial Cockpit

## Summary
Evoluir o Dashboard Executivo para ser o cockpit diario da operacao comercial da ProGym:
follow-ups de leads, alunos em atencao (risco/renovacao), acoes do dia e funil semanal
esforco->resultado, cada item com deep-link para a tela de execucao existente.

> **Metodo:** este milestone roda no protocolo multi-agente (a360). Os artefatos
> executaveis estao em `docs/ROADMAP.md` (M1) e `specs/slots/M1/{cockpit-api,funnel-api,
> cockpit-ui}/` (BRIEF + DESIGN-SPEC + CONTRACT por slot). Este arquivo preserva a
> numeracao viva das specs de produto.

## Goals
- Rotina da manha inteira sem planilha paralela (criterio de sucesso do fundador).
- Endpoint agregado `GET /api/cockpit/daily` (3 listas com deep-link).
- Endpoint `GET /api/cockpit/weekly-funnel` (contatos -> respostas -> conversoes, vs. semana anterior).
- Bloco "Hoje" no Dashboard Executivo, desktop-first, componentes ui2 existentes.

## Non-goals
- R$ atribuido as acoes (M2+). Threading de resposta por conversa Kommo (M2+).
- Tela nova, mudanca de schema de banco, mudanca nas telas de execucao existentes.

## Acceptance Criteria
Ver criterios HTC em `docs/ROADMAP.md` (M1) — aprovacao do fundador e gate de fechamento.
