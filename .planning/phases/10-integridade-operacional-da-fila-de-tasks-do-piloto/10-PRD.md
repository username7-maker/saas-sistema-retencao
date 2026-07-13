# Phase 10 - PRD: Integridade operacional da fila de tasks do piloto

**Status:** ready for planning; structural concurrency split to Phase 10.1
**Created:** 2026-07-13  
**Surfaces:** `/tasks`, `/ai/triage`, Work Queue API, AI triage e efeitos externos do Autopilot

## Problema

A fila unificada reduziu a navegacao entre telas, mas ainda nao pode ser tratada como fonte operacional confiavel. O piloto possui mais itens do que a primeira pagina fixa consegue expor; busca e selecao operam apenas sobre o recorte ja carregado; contadores podem parecer zero antes de a consulta correspondente rodar; e recomendacoes de IA podem sugerir `Criar tarefa` mesmo quando o aluno ja possui trabalho aberto equivalente.

O mesmo contrato tambem mistura estados planejados, executaveis e aguardando resultado. A ausencia de claim concorrente e de uma garantia persistente de idempotencia em rotas humanas foi confirmada, mas exige migration e prova com duas sessoes PostgreSQL; esse fechamento estrutural foi isolado na Phase 10.1 para nao bloquear nem fragilizar o P0 verificavel desta fase.

## Resultado esperado

Ao abrir a fila, o operador deve enxergar uma representacao honesta do snapshot do tenant e do turno escolhido. Toda acao carregada pelas fontes deve ser pesquisavel e alcancavel; limites internos devem ser declarados; uma recommendation deve reutilizar task ativa equivalente; e um item adiado nao pode continuar aparecendo em `Fazer agora`.

## Requisitos funcionais

1. A API deve paginar e pesquisar antes de materializar a pagina, retornando metadados suficientes para navegar por todos os resultados elegiveis.
2. Contagens devem vir de consulta autoritativa coerente com os filtros da fila e possuir estado explicito de carregamento/erro na UI.
3. Uma recomendacao que ja possua task ativa equivalente deve oferecer continuacao/foco nessa task, nao criacao de outra.
4. A deduplicacao ativa deve ser garantida na persistencia ou por mecanismo transacional equivalente, nao apenas por consulta otimista na aplicacao.
5. Sinais ausentes devem permanecer `unknown`; nao podem ser convertidos silenciosamente em score zero ou severidade critica.
6. Frescor, responsavel/equipe, prazo e motivo decisivo devem estar presentes ou explicitamente ausentes antes da execucao.
7. Snooze deve retirar o item de `do_now` ate o instante configurado. Empates de prioridade devem favorecer o prazo mais proximo e depois uma chave estavel.
8. `/tasks` e `/ai/triage` devem compartilhar o mesmo comportamento e a mesma suite de regressao do runner.

## Requisitos estruturais transferidos para Phase 10.1

- Claim/versao com conflito recuperavel e deduplicacao canonica sob concorrencia.
- Consentimento por canal/efeito, intent duravel e chave idempotente unica antes do provider.
- Harness PostgreSQL com duas sessions e provider sintetico; mocks unitarios nao fecham esses requisitos.

## Requisitos de experiencia

- Preservar o modo execucao staff-first e o inspector em duas colunas no desktop.
- Busca deve consultar o servidor com feedback de carregamento e manter filtros atuais.
- A fila deve oferecer navegacao incremental clara (`Carregar mais` ou paginacao equivalente) e informar faixa/total real.
- Contadores nunca exibem um zero falso; durante consulta mostram estado de carregamento discreto.
- CTA de recomendacao duplicada deve dizer `Continuar tarefa` ou `Abrir tarefa existente`.
- Item desatualizado, sem owner ou sem prazo deve comunicar a lacuna e impedir a acao apenas quando ela realmente inviabilizar execucao segura.
- Snooze concluido deve remover imediatamente o item da lista `Fazer agora` e confirmar quando ele voltara.
- Nao redesenhar a lista completa legada nesta fase.

## Guardrails

- Sem envio externo autonomo.
- Sem acesso cross-tenant ou ampliacao de RBAC para acomodar a UI.
- Sem transformar `WorkQueueItem` em novo ledger generico; `Task` continua sendo o ledger operacional.
- Sem backfill destrutivo de historico do piloto.
- Sem depender de credenciais reais nos testes; usar fixtures sinteticas.
- Toda alteracao em WhatsApp, consentimento, tenant ou transacao exige teste de regressao dedicado.

## Criterios de aceite

- Um dataset sintetico com 188 itens permite localizar e abrir qualquer item alem da primeira pagina.
- Busca por aluno/item presente apenas depois da posicao 25 retorna o resultado correto.
- Total e contagens permanecem coerentes ao trocar estado, dominio, turno e bucket.
- Preparar duas vezes a mesma recomendacao ativa retorna a mesma task ou conflito idempotente; nunca cria duas tasks.
- Item snoozed nao aparece em `do_now` antes do prazo; ordenacao resolve empate pelo menor `due_at`.
- Testes backend focados, testes frontend das duas superficies, typecheck, lint focal e build passam.
- Smoke publicado usa apenas conta/fixture sintetica e separa backend, frontend e itens nao verificaveis sem credencial.
- A fase nao declara WQ-06/WQ-07 concluidos; ambos permanecem rastreados na Phase 10.1.

## Fora do escopo

- Redesign amplo de Tasks ou do design system Cordex.
- Novo motor generico de BPM/workflow.
- Envio autonomo via WhatsApp ou Kommo.
- Dashboard executivo completo de produtividade, capacidade e ROI.
- Reclassificacao retroativa de todo o historico de tasks.
