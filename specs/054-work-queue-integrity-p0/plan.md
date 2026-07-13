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
2. Persistir o vinculo preparado e retornar a mesma task em repeticoes.
3. Preservar `unknown` para sinais ausentes e expor frescor/prontidao no payload.
4. Cobrir task reutilizavel, encerrada, arquivada, cross-tenant e preparacao repetida.

## Wave 3 - Concurrency and External Effects

1. Introduzir claim/versao compatibilidade-preservada para execucao e outcome.
2. Responder conflito concorrente sem sobrescrita silenciosa.
3. Aplicar consentimento conforme canal/efeito em todos os caminhos humanos relevantes.
4. Persistir chave idempotente unica e estado do efeito antes/depois do provider.
5. Cobrir concorrencia, retry, falha de provider, consentimento e isolamento de tenant.

## Wave 4 - Shared Runner and Pilot Gate

1. Enviar busca/filtros/pagina para a API e consumir o envelope autoritativo.
2. Implementar navegacao, loading honesto, aviso de truncamento, CTA de reuso, stale/claim/conflict e feedback de snooze.
3. Validar `/tasks` e `/ai/triage` com a mesma suite do runner.
4. Rodar testes backend, frontend, typecheck, lint focal, build, `specify check` e smoke sintetico separado por backend/frontend.

## Risk Control

- Contrato aditivo para nao quebrar consumidores existentes.
- Nenhuma alteracao visual ampla nos componentes legados dirty.
- Migracoes aditivas com downgrade e validacao de concorrencia quando Wave 3 exigir persistencia.
- Nenhuma credencial ou dado real do piloto em testes/smoke.
- Publicacao somente depois de backend e frontend estarem compativeis entre si.
