# Plan 054 - Work Queue Integrity P0

## Architecture

Preservar `Task` e `AITriageRecommendation` como fontes persistentes e `WorkQueueItem` como contrato semantico derivado. Evoluir o contrato de lista de forma aditiva e concentrar regras de estado, busca, contagem, ordenacao e deduplicacao nos services de backend. O frontend apenas representa o contrato autoritativo.

## Wave 1 - Reachability and Truth

1. Adicionar request de busca e envelope tipado de lista com `items`, `total`, `page`, `page_size`, `state_counts` e `truncated_sources`.
2. Aplicar busca normalizada, filtros e ordenacao antes da paginacao.
3. Tornar snooze/visibilidade e desempate de prazo semanticamente consistentes.
4. Cobrir pagina 2, busca alem dos 25 primeiros, contagens cruzadas, truncamento e tenant scope.

## Wave 2 - AI Reuse and Readiness

1. Localizar task ativa de onboarding equivalente antes de criar nova task.
2. Persistir o vinculo preparado e retornar a mesma task em repeticoes sequenciais, sem alegar concorrencia.
3. Preservar `unknown` para sinais ausentes e expor frescor/prontidao no payload.
4. Cobrir task reutilizavel, encerrada, arquivada, cross-tenant e preparacao repetida sequencial/non-concurrent.

## Wave 3 - Shared Runner and Pilot Gate

1. Enviar busca/filtros/pagina para a API e consumir o envelope autoritativo.
2. Implementar navegacao, loading honesto, aviso de truncamento, CTA de reuso, stale/unknown/readiness e feedback de snooze.
3. Validar `/tasks` e `/ai/triage` com a mesma suite do runner.
4. Rodar testes backend, frontend, typecheck, lint focal, build, `specify check` e smoke sintetico separado por backend/frontend.

## Risk Control

- Contrato aditivo para nao quebrar consumidores existentes.
- Nenhuma alteracao visual ampla nos componentes legados dirty.
- Nenhuma migration ou prova de concorrencia pertence a esta fase; persistencia estrutural fica somente na Spec 055 / Phase 10.1.
- Nenhuma credencial ou dado real do piloto em testes/smoke.
- Publicacao somente depois de backend e frontend estarem compativeis entre si.
- Toda referencia a claim/CAS, consentimento, idempotencia de efeitos, migration e prova PostgreSQL pertence somente a Spec 055 / Phase 10.1.
