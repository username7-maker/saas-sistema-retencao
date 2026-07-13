# Spec 054 - Work Queue Integrity P0

## User Story

Como operador, gestor ou professor do Cordex Gym OS, quero navegar e pesquisar o snapshot inteiro da fila operacional, sem contagens falsas ou criacao sequencial de tasks equivalentes, para saber o que fazer agora e quando um limite tecnico ainda impede total exato.

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
- Preparacao repetida sequencialmente, sem concorrencia, da mesma recommendation deve convergir para a mesma task; garantia concorrente pertence a Spec 055 / Phase 10.1.
- Sinal ausente permanece `unknown`; ausencia de dado nao pode virar automaticamente score zero ou severidade critica.
- Item executavel deve explicitar frescor, owner/equipe, prazo e motivo ou a ausencia desses dados.

### Estado

- Snooze deve usar uma fonte temporal canonica e retirar o item de `do_now` ate o instante configurado.
- Em empate de prioridade, menor prazo vence; a ordenacao final deve possuir chave estavel.

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
- Claim/CAS e hardening de efeitos externos; rastreados na Spec 055 / Phase 10.1.

## Acceptance Criteria

- Dataset sintetico com 188 itens permite abrir pagina 2 e localizar por busca um item originalmente posterior a posicao 25.
- Resposta informa `total`, pagina, tamanho, contagens por estado e fontes truncadas sem afirmar exatidao falsa.
- UI mostra carregamento de contagem sem usar `0` provisoriamente e exibe faixa/total ou indicacao de limite inferior.
- Recommendation de onboarding com task ativa retorna a task existente e nao aumenta o numero de tasks.
- Duas preparacoes sequenciais e non-concurrent da mesma recommendation convergem para o mesmo resultado; este criterio nao cobre corrida entre sessions.
- Item snoozed desaparece de `do_now` e reaparece apenas no instante correto.
- Tenant isolation, testes focados, typecheck, lint focal, build e `specify check` passam.

## Constitutional Alignment

- Operational Truth: totais, estados e CTAs derivam do backend persistido.
- Human Review: comunicacao continua humana e efeitos bloqueados ficam explicitos.
- Tenant Isolation: busca e reuso sequencial permanecem tenant-scoped; claim/CAS e idempotencia estrutural sao tratados apenas na Spec 055 / Phase 10.1.
- Durable Side Effects: esta fase nao amplia efeitos; o fechamento estrutural fica explicitamente rastreado na Spec 055.
- Shared Semantic Payload: as duas superficies usam o mesmo `WorkQueueItem` e o mesmo contrato de lista.
