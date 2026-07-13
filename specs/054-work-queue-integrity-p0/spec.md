# Spec 054 - Work Queue Integrity P0

## User Story

Como operador, gestor ou professor do Cordex Gym OS, quero confiar que a fila operacional mostra todo o trabalho elegivel, sem duplicatas ou contagens falsas, e que assumir, adiar, executar ou preparar uma comunicacao produz exatamente um resultado seguro e auditavel.

## Requirements

### Alcance e verdade da fila

- `GET /api/v1/work-queue/items` deve aceitar busca server-side e devolver metadados de paginacao e contagens autoritativas.
- Busca, filtros, ordenacao e classificacao de estado devem ocorrer antes do recorte de pagina.
- Contagens devem respeitar turno, responsavel, dominio, origem, bucket e busca, ignorando apenas o tab de estado quando alimentarem os tabs.
- Se uma origem ainda depender de teto tecnico, a resposta deve sinalizar truncamento; a UI nao pode apresentar um limite inferior como total exato.
- `/tasks` e `/ai/triage` devem permitir navegar por todas as paginas e localizar um item que nao estava nos primeiros 25 resultados.

### Unicidade e prontidao

- Uma recomendacao de onboarding deve reutilizar uma task ativa equivalente quando ela existir.
- Task encerrada, cancelada, deletada, arquivada ou de outro tenant nunca pode ser reutilizada.
- Preparacao repetida da mesma recommendation deve ser idempotente.
- Sinal ausente permanece `unknown`; ausencia de dado nao pode virar automaticamente score zero ou severidade critica.
- Item executavel deve explicitar frescor, owner/equipe, prazo e motivo ou a ausencia desses dados.

### Estado e concorrencia

- Snooze deve usar uma fonte temporal canonica e retirar o item de `do_now` ate o instante configurado.
- Em empate de prioridade, menor prazo vence; a ordenacao final deve possuir chave estavel.
- Claim/outcome deve usar versao ou precondicao equivalente para que dois operadores nao atualizem silenciosamente o mesmo item.
- Conflito concorrente deve retornar resposta recuperavel e auditavel.

### Efeitos externos

- A politica de consentimento deve ser avaliada conforme canal e efeito concreto, inclusive em fluxo humano ou send-and-wait.
- Todo efeito externo deve possuir chave idempotente persistida e unica no escopo correto.
- Repetir a mesma requisicao nao pode chamar o provider uma segunda vez.
- O estado deve distinguir preparado, enviado/confirmado, falhou e aguardando resultado.
- Nao ha autoenvio nesta fase.

### Qualidade e seguranca

- Toda leitura e escrita permanece filtrada por `gym_id` e RBAC atual.
- Testes usam somente tenants, membros, consentimentos e providers sinteticos.
- Backend e frontend devem possuir regressao focada para as duas superficies consumidoras do runner.

## Non-Goals

- Redesign amplo da lista completa de tasks.
- Novo motor generico de workflow ou tabela `work_items`.
- Envio autonomo por WhatsApp, Kommo ou outro provider.
- Dashboard executivo completo de capacidade/ROI.
- Backfill destrutivo do historico do piloto.

## Acceptance Criteria

- Dataset sintetico com 188 itens permite abrir pagina 2 e localizar por busca um item originalmente posterior a posicao 25.
- Resposta informa `total`, pagina, tamanho, contagens por estado e fontes truncadas sem afirmar exatidao falsa.
- UI mostra carregamento de contagem sem usar `0` provisoriamente e exibe faixa/total ou indicacao de limite inferior.
- Recommendation de onboarding com task ativa retorna a task existente e nao aumenta o numero de tasks.
- Duas preparacoes repetidas da mesma recommendation convergem para o mesmo resultado.
- Item snoozed desaparece de `do_now` e reaparece apenas no instante correto.
- Dois claims/outcomes concorrentes resultam em um vencedor e um conflito explicito.
- Efeito externo bloqueado por consentimento nao chama provider; repeticao idempotente chama provider no maximo uma vez.
- Tenant isolation, testes focados, typecheck, lint focal, build e `specify check` passam.

## Constitutional Alignment

- Operational Truth: totais, estados e CTAs derivam do backend persistido.
- Human Review: comunicacao continua humana e efeitos bloqueados ficam explicitos.
- Tenant Isolation: dedupe, claim e idempotencia sao sempre tenant-scoped.
- Durable Side Effects: intencao e resultado externo ficam persistidos e recuperaveis.
- Shared Semantic Payload: as duas superficies usam o mesmo `WorkQueueItem` e o mesmo contrato de lista.
