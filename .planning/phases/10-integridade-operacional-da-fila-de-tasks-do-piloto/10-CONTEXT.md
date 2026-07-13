# Phase 10 - Contexto e decisoes

## Origem

A fase nasce de auditoria tecnica, estrutural e operacional da fila publicada do Cordex Gym OS. A auditoria comparou o comportamento visivel no piloto com os contratos reais de frontend, backend, modelos e testes existentes.

## Decisoes de produto ja tomadas

- `Task` permanece o ledger operacional; `WorkQueueItem` continua sendo contrato semantico derivado.
- `/tasks` e `/ai/triage` continuam compartilhando `WorkExecutionView`.
- A experiencia principal continua staff-first, orientada a uma acao clara por vez.
- Efeitos externos permanecem humanos, visiveis e auditaveis.
- Item critico/degradado continua exigindo confirmacao curta.
- A lista completa legada e seus ajustes visuais ficam fora deste corte.

## Prioridade do corte

1. Nenhum trabalho invisivel: alcance, busca e contagem server-side.
2. Nenhum trabalho artificial: reuso e deduplicacao de task ativa.
3. Nenhuma execucao ambigua: frescor, owner, prazo, estado, snooze e ordenacao.
4. Nenhuma colisao silenciosa: claim/versao.
5. Nenhum efeito externo inseguro: consentimento aplicavel e idempotencia persistente.
6. Nenhuma conclusao sem prova: suites focadas e smoke sintetico.

## Contrato de interface

### Fila

- Busca remota com debounce, estado de carregamento e mensagem de erro recuperavel.
- Navegacao incremental preservando item selecionado quando ele ainda pertence ao resultado.
- Total autoritativo exibido como dado da API, nunca inferido de `items.length`.
- Contadores com skeleton/ellipsis enquanto carregam, sem placeholder numerico enganoso.

### Item e CTA

- Recomendacao com task ativa: `Continuar tarefa` como CTA principal e link para a task canonica.
- Item snoozed: ausente de `Fazer agora` ate `visible_from`/prazo canonico.
- Dado desconhecido: rotulo `Nao informado` ou `Sem dado`, sem cor critica automatica.
- Recomendacao stale: aviso de atualizacao e CTA seguro para recalcular/atualizar antes de executar quando necessario.
- Item assumido: nome do responsavel e conflito explicito para outro operador.

### Feedback

- Claim bem-sucedido atualiza a fila e o inspector sem reload integral.
- Conflito 409 preserva contexto, informa que o item mudou e oferece `Atualizar fila`.
- Snooze confirma data/hora de retorno e retira o card imediatamente.
- Repeticao idempotente reapresenta o resultado anterior, sem segundo efeito no provider.

## Compatibilidade e acessibilidade

- Reutilizar componentes/tokens Cordex existentes; nenhuma nova linguagem visual.
- Estados nao podem depender apenas de cor.
- Controles de busca, paginacao, filtros, claim e refresh devem ser acessiveis por teclado e ter nome discernivel.
- Mobile empilha fila e inspector sem esconder acesso a paginacao ou ao estado do claim.

## Fora do corte

- Mudanca visual ampla na lista completa.
- Automacao de envio.
- Novas permissoes.
- Metricas executivas completas.
