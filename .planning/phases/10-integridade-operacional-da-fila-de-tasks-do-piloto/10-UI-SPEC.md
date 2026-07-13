---
phase: 10
slug: integridade-operacional-da-fila-de-tasks-do-piloto
status: approved
shadcn_initialized: false
preset: none
created: 2026-07-13
---

# Phase 10 — UI Design Contract

> Contrato visual e de interação para a integridade operacional da Work Queue em `/tasks` e `/ai/triage`. Gerado por `gsd-ui-researcher`; deve ser validado por `gsd-ui-checker` antes da execução.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | Cordex Design System manual sobre Tailwind CSS 3 |
| Preset | Não aplicável; `components.json` não existe e esta fase não inicializa shadcn |
| Component library | Componentes internos `src/components/ui` e `src/components/ui2`; sem Radix/Base UI |
| Icon library | `lucide-react` |
| Font | Inter no corpo; Barlow Condensed/Space Grotesk em títulos; JetBrains Mono apenas para números tabulares |

### Locked visual direction

- Preservar o dark técnico Cordex, seus tokens `lovable-*`, as superfícies em camadas e o azul como núcleo de ação.
- Preservar a estrutura staff-first atual: controles, fila selecionável e inspector. Não redesenhar a lista completa legada.
- `/tasks` e `/ai/triage` devem renderizar o mesmo contrato por meio de `WorkExecutionView`; diferenças ficam restritas a título, subtítulo e filtro inicial já aceitos pelo componente.
- Não instalar biblioteca, registry, preset ou componente externo nesta fase.
- Não criar uma nova linguagem de cards, badges ou alertas. Evoluir os componentes Cordex existentes de forma aditiva.

### Existing component inventory

| Need | Existing component/pattern | Contract for Phase 10 |
|------|----------------------------|-----------------------|
| Primary/secondary actions | `ui2/Button` | Reusar variantes `primary`, `secondary`, `ghost` e `danger`; nunca criar botão ad hoc para refresh ou retry |
| Search and date | `ui2/Input` | Reusar foco, altura e tokens; busca ganha label discernível, clear e busy state; data ganha label visível |
| State/status labels | `ui2/Badge` | Reusar `neutral`, `info`, `warning`, `danger` e `success`; todos os estados devem ter texto, não apenas cor |
| Page navigation | `ui2/Pagination` | Estender para faixa/total honesto, nomes acessíveis, loading e total truncado; não duplicar paginação dentro do runner |
| Initial loading | `ui/SkeletonList`, `ui2/Skeleton` | Skeleton apenas na primeira carga; atualização subsequente preserva conteúdo e expõe busy state discreto |
| Empty result | `ui/EmptyState` | Reusar com copy específica para fila vazia versus busca sem resultado |
| Notes | `ui2/Textarea` | Preservar rascunho durante refresh da fila |
| Inline recovery | Cordex surface + `Button` | Usar bloco inline no inspector/lista; não introduzir modal para erro recuperável ou snooze |
| Toast/announcement | `react-hot-toast` + live region do runner | Toast é feedback complementar; mudança crítica também permanece visível no contexto da fila |

---

## Layout Contract

### Desktop (`xl`, 1280px ou maior)

- Preservar o grid de duas colunas existente: fila com mínimo de 340px e inspector com mínimo de 460px, separados por 24px.
- O inspector permanece `sticky` abaixo do topbar (`top-24`) e não muda de posição durante atualização de busca, contagem ou página.
- Paginação e faixa de resultados pertencem ao rodapé visual da coluna da fila, nunca ao inspector.
- O bloco de filtros continua acima das duas colunas. As categorias são agrupadas por significado, na ordem: domínio, estado, turno e subcategoria.

### Tablet e mobile (abaixo de 1280px)

- Usar uma coluna na ordem DOM: controles → lista → paginação/faixa → inspector.
- O inspector deixa de ser sticky. Nenhuma ação de refresh ou snooze pode depender de hover ou ficar fora de um drawer oculto.
- A paginação permanece imediatamente após os cards, antes do inspector, e nunca é removida para economizar espaço.
- Grupos de filtro podem quebrar linha; não truncar labels críticos como `Aguardando resultado` ou `Resultado parcial`.
- Em ponteiro coarse/mobile, controles desta fase devem ter área interativa mínima de 40px de altura. No desktop denso, o mínimo é 32px, coerente com `Button size="sm"` e acima do mínimo WCAG de 24px.

### Stable regions

- A primeira carga reserva altura para lista e inspector com skeletons, evitando salto entre uma e duas colunas.
- Busca, paginação e background refresh mantêm a página anterior visível com `aria-busy="true"`; não trocar toda a tela por skeleton.
- A seleção usa a chave estável `source_type:source_id`. Após revalidação do mesmo conjunto, preservar o item se ainda estiver na resposta; caso contrário, selecionar o primeiro item elegível.
- Ao trocar de página deliberadamente, selecionar o primeiro item da página de destino. Ao retornar à página anterior, restaurar a seleção anterior se ela ainda existir nessa página.

---

## Spacing Scale

Declared values (all multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Espaço entre ícone e texto curto, status inline |
| sm | 8px | Gap entre botões compactos e badges |
| md | 16px | Padding padrão de card, callout e controles |
| lg | 24px | Padding do inspector e separação de blocos operacionais |
| xl | 32px | Separação entre regiões maiores em mobile |
| 2xl | 48px | Respiro de empty/error state |
| 3xl | 64px | Somente separação de página quando já existente |

Exceptions: none. Controles compactos usam 8px ou 16px conforme o componente; o gap entre fila e inspector usa 24px.

---

## Typography

As adições da Phase 10 usam exatamente quatro tamanhos e dois pesos. Títulos preexistentes em `font-bold` ficam preservados, mas não devem gerar uma terceira variação nova.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Supporting/body | 14px | 400 | 1.5 |
| Label/status | 12px | 600 | 1.4 |
| Card/action title | 16px | 600 | 1.35 |
| Section heading | 24px | 600 | 1.2 |

- Números de contagem e faixa podem usar JetBrains Mono com `font-variant-numeric: tabular-nums`; texto adjacente permanece Inter.
- Labels em caixa alta continuam restritos aos pequenos overlines já existentes; mensagens de erro, stale e truncamento usam sentence case.
- Não reduzir textos operacionais abaixo de 12px.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `hsl(var(--lovable-bg))`; dark `#0A0B0F` | Fundo da página e espaço estrutural |
| Secondary (30%) | `hsl(var(--lovable-surface))`; dark `#0E1018` | Painéis, cards, inspector e estados elevados |
| Accent (10%) | `hsl(var(--lovable-primary))`; dark `#3B82F6` | Item selecionado, filtro ativo, foco, primary CTA e página atual |
| Destructive/safety block | `hsl(var(--lovable-danger))`; dark `#FF3B3B` | Somente bloqueio de segurança, erro que impede ação ou ação destrutiva existente |

Accent reserved for: item selecionado; estado/filtro ativo; primary CTA disponível; foco visível; página atual; progresso/busy discreto. O azul não marca dado desconhecido, stale ou erro.

O foco visual primário é o CTA do item selecionado no inspector; o card selecionado e os filtros ativos são âncoras secundárias.

Semantic use:

- `warning` (`#F59E0B` no dark): recomendação stale, total parcial e lacuna que merece atenção.
- `danger` (`#FF3B3B` no dark): falha impeditiva ou ação destrutiva. Não usar em `unknown`.
- `success` (`#10B981` no dark): snooze persistido ou outcome confirmado. Não usar para indicar apenas origem de IA.
- `neutral`: `Sem dado`, `Sem prazo`, `Sem responsável`, atualização desconhecida e estados informativos sem urgência comprovada.

Todo uso semântico combina cor + texto e, nos callouts, ícone. Nenhuma diferença de estado depende apenas da borda ou do preenchimento.

---

## Interaction Contract

### 1. Remote search

1. O campo mantém o placeholder `Buscar aluno, motivo ou ação...` e recebe label discernível `Buscar na fila operacional`.
2. Aplicar debounce de 300ms sobre o valor com `trim`; `Enter` dispara imediatamente a busca pendente.
3. Toda nova busca volta para a página 1 e mantém domínio, estado, turno, origem e bucket atuais.
4. Enquanto a nova busca roda, manter a lista anterior visível, desabilitar apenas controles que poderiam disparar a mesma navegação e mostrar spinner/skeleton de 16px dentro do campo com o status `Buscando na fila...`.
5. Exibir botão de limpar somente quando houver texto, com nome acessível `Limpar busca`. Ao limpar, voltar para página 1.
6. Se a busca falhar, manter o último resultado bem-sucedido e mostrar abaixo do campo: `Não foi possível buscar na fila.` + botão `Tentar novamente`.
7. Se a busca concluir sem itens, usar o empty state específico, não o empty state de fila resolvida.

### 2. Authoritative state counts

| State | Visual copy | Accessible name |
|-------|-------------|-----------------|
| Initial loading | `Fazer agora (…)` | `Fazer agora, contagem carregando` |
| Exact | `Fazer agora (188)` | `Fazer agora, 188 ações` |
| Truncated/lower bound | `Fazer agora (188+)` | `Fazer agora, pelo menos 188 ações` |
| Count error | `Fazer agora (—)` | `Fazer agora, contagem indisponível` |
| Background refresh, same filters | Manter o último número com indicador `Atualizando` | Acrescentar `contagem atualizando` ao nome |

- Aplicar o mesmo contrato a `Aguardando resultado`.
- Ao mudar busca ou filtro, não reutilizar visualmente a contagem antiga como se fosse do novo conjunto; usar `…` até a resposta nova.
- Falha de contagem não bloqueia leitura da página já carregada. Mostrar callout compacto: `Não foi possível atualizar as contagens.` + `Atualizar fila`.
- Botões de estado usam `aria-pressed`; não são tabs de navegação de página.

### 3. Pagination and range

- Reusar `Pagination` com `Anterior`, páginas numeradas e `Próximo`.
- Total exato: `Mostrando 26–50 de 188 ações`.
- Resultado truncado: `Mostrando 1–25 de pelo menos 188 ações` e badge `Resultado parcial`.
- Explicação do truncamento, sempre visível perto da faixa: `Uma ou mais origens atingiram o limite técnico. Refine os filtros ou atualize a fila.`
- Em total truncado, a quantidade de páginas refere-se ao recorte conhecido e deve ser anunciada como `Página X de Y no recorte disponível`.
- Durante troca de página, manter a página atual visível com opacidade normal, marcar a região como busy, desabilitar os controles de paginação e anunciar `Carregando página N...`.
- Falha ao carregar página mantém a página anterior e mostra `Não foi possível carregar a página N.` + `Tentar novamente`.
- Após sucesso iniciado por teclado, mover foco para o primeiro card da nova página e anunciar a nova faixa. Clique/pointer não força mudança de foco.
- `Anterior` e `Próximo` permanecem disponíveis no mobile; páginas intermediárias podem ser reduzidas a ellipsis, nunca esconder ambos os controles de direção.

### 4. Selection and refresh

- O card selecionado usa azul + `aria-current="true"` ou `aria-pressed="true"` e continua identificável por texto para quem não percebe cor.
- Background refresh preserva a seleção se a mesma chave continuar elegível.
- Se o item sair por outcome, snooze ou alteração de filtro, selecionar o próximo card na mesma posição; se não houver, selecionar o anterior; se a lista esvaziar, focar o heading do empty state.
- `Atualizar fila` preserva busca, filtros, página e observação digitada. Só limpa o rascunho depois de mutação confirmada ou ação explícita do operador.
- A atualização não faz reload integral da rota.

---

## Item and Inspector Contract

### Card anatomy

Manter a hierarquia atual e acrescentar integridade sem virar uma nuvem de badges:

1. Linha de badges: severidade textual, domínio, turno e no máximo dois estados adicionais relevantes (`Dados desatualizados`, `Resultado parcial`).
2. Nome do aluno/lead.
3. `Fazer agora: {ação}`.
4. Motivo decisivo em até duas linhas.
5. Rodapé: origem à esquerda; prazo e responsável à direita, permitindo quebra no mobile.
6. Lacunas de prontidão aparecem em uma linha textual: `Pendências: responsável, prazo`, não como quatro badges vermelhos.

### Existing canonical task

Quando a recommendation aponta para uma task ativa equivalente:

- Substituir qualquer `Criar tarefa` por `Continuar tarefa` no card, no inspector e no primary CTA.
- Mostrar suporte: `Já existe uma tarefa ativa para esta necessidade. Continue nela para preservar responsável, prazo e histórico.`
- O CTA abre/seleciona a task canônica; não chama criação novamente.
- Se o vínculo canônico não puder ser recuperado, mostrar `Tarefa vinculada indisponível.` + `Atualizar fila`; nunca oferecer criação silenciosa como fallback.

### Freshness and unknown data

| Backend state | UI contract | Execution behavior |
|---------------|-------------|--------------------|
| `fresh` | No badge obrigatório; detalhes podem mostrar `Atualizado há {tempo}` | Fluxo normal |
| `stale`, non-blocking | Badge warning `Dados desatualizados`; texto `Esta recomendação pode não refletir o estado atual do aluno.`; ação secundária `Atualizar recomendação` | Primary CTA permanece disponível somente se o backend declara execução segura |
| `stale`, blocking | Mesmo callout; primary CTA vira `Atualizar recomendação` | Demais ações de execução ficam desabilitadas até novo snapshot |
| `unknown` | Badge neutral `Atualização não informada` | Não elevar severidade nem bloquear por inferência da UI |

Rótulos canônicos de ausência:

- Owner: `Sem responsável`.
- Equipe: `Equipe não informada`.
- Prazo: `Sem prazo`.
- Turno: `Turno não informado`.
- Sinal/score: `Sem dado`.
- Frescor: `Atualização não informada`.
- Severidade ausente: `Prioridade não informada`, variant neutral.

A UI apenas bloqueia ação quando recebe motivo de bloqueio explícito. Owner ou prazo ausente é comunicado, mas não vira bloqueio automático por decisão do frontend.

### Snooze

- Preservar a seção `Adiar corretamente` com opções `Amanhã`, `Próxima semana` e customização.
- O input customizado possui label visível `Data de retorno`; o botão usa `Adiar para esta data`.
- A data/hora exibida na confirmação vem da resposta canônica do backend e do timezone da academia; o frontend não monta `09:00Z` como verdade operacional.
- Ao confirmar, retirar imediatamente o item de `Fazer agora`, selecionar o próximo item e anunciar `Adiado até {dd/mm} às {hh:mm}.`
- A confirmação aparece como toast e live region; não exige modal, pois a ação é recuperável e não destrutiva.
- Se falhar, manter/restaurar o card e mostrar `Não foi possível adiar. Tente novamente.`

### Deferred interaction contract

Claim/version e consentimento/idempotência de efeitos externos pertencem à Phase 10.1 / Spec 055. Esta fase não adiciona CTAs, badges, bloqueios ou mensagens para esses estados e não pode declará-los validados. A estrutura do runner deve apenas permanecer aditiva para receber esses campos depois.

---

## State Matrix

| Surface state | List | Inspector | Recovery |
|---------------|------|-----------|----------|
| Initial loading | 6 linhas de `SkeletonList`; controles visíveis; contagens `…` | Skeleton de título, contexto e CTA | Automático |
| Background fetching | Conteúdo anterior preservado + busy indicator | Item atual preservado | Automático ou `Atualizar fila` se falhar |
| Exact empty queue | `Fila em dia` | Oculto | `Todos os turnos` apenas quando permitido por RBAC |
| Search/filter empty | `Nenhuma ação encontrada` | Oculto | `Limpar busca e filtros` |
| Initial list error | `Não foi possível carregar a fila operacional.` | Oculto | `Tentar novamente` |
| Search error | Último resultado preservado | Item atual preservado | `Tentar novamente` abaixo da busca |
| Count error | Tabs com `—`; lista pode continuar | Sem alteração | `Atualizar fila` |
| Page error | Página anterior preservada | Item anterior preservado | `Tentar novamente` |
| Truncated snapshot | Cards e paginação do recorte | Inspector normal | Badge `Resultado parcial` + explicação |
| Stale recommendation | Card warning textual | Callout + refresh | `Atualizar recomendação` |
| Snooze success | Card removido e próximo selecionado | Atualiza para próximo | Live/toast com retorno |

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA — canonical task | `Continuar tarefa` |
| Primary CTA — stale blocking | `Atualizar recomendação` |
| Empty queue heading | `Fila em dia` |
| Empty queue body | `Nenhuma ação exige execução neste filtro agora.` |
| Search empty heading | `Nenhuma ação encontrada` |
| Search empty body | `Revise a busca ou limpe os filtros para ver outras ações.` |
| Search empty action | `Limpar busca e filtros` |
| Initial error | `Não foi possível carregar a fila operacional.` |
| Search error | `Não foi possível buscar na fila.` |
| Count error | `Não foi possível atualizar as contagens.` |
| Page error | `Não foi possível carregar a página {N}.` |
| Generic retry | `Tentar novamente` |
| Queue refresh | `Atualizar fila` |
| Truncated badge | `Resultado parcial` |
| Truncated explanation | `Uma ou mais origens atingiram o limite técnico. Refine os filtros ou atualize a fila.` |
| Existing task support | `Já existe uma tarefa ativa para esta necessidade. Continue nela para preservar responsável, prazo e histórico.` |
| Stale badge | `Dados desatualizados` |
| Stale support | `Esta recomendação pode não refletir o estado atual do aluno.` |
| Unknown freshness | `Atualização não informada` |
| Snooze success | `Adiado até {dd/mm} às {hh:mm}.` |
| Snooze error | `Não foi possível adiar. Tente novamente.` |
| Destructive confirmation | Nenhuma nova ação destrutiva. Manter a confirmação curta já existente para item crítico/degradado: `Confirmar e começar` / `Voltar para o item` |

Copy rules:

- Usar português do Brasil com acentuação correta.
- Preferir verbo + objeto em CTA; não usar `OK`, `Sim` ou `Continuar` isolado.
- Não chamar limite inferior de `total`, dado desconhecido de `crítico`, intent de `enviado` ou replay de `novo envio`.
- Explicações têm no máximo duas frases curtas; detalhes técnicos ficam recolhidos em `Ver detalhes`.

---

## Accessibility Contract

### Semantics and names

- Agrupar botões com `role="group"` e nomes `Filtrar por domínio`, `Filtrar por estado`, `Filtrar por turno` e `Filtrar por categoria`.
- Botões de filtro expõem `aria-pressed`; o rótulo visual selecionado não depende de cor.
- Busca tem `<label>` visível ou `sr-only`; clear, retry, refresh e paginação possuem nomes discerníveis.
- Região de resultados usa heading próprio, `aria-busy` e live region `polite` para faixa, busca, página e snooze.
- Erro impeditivo usa `role="alert"`; mensagens informativas usam `role="status"`.
- Skeletons são `aria-hidden="true"`; um texto único anuncia o carregamento.
- Card selecionável deve ter nome que inclua sujeito e ação; razão, prazo, responsável e lacunas ficam ligados via `aria-describedby`.
- Inspector usa heading ligado ao sujeito selecionado; seu primary CTA deve ser alcançável por teclado sem atravessar controles invisíveis.

### Keyboard and focus

- Ordem de tabulação segue a ordem visual/DOM, sem `tabIndex` positivo.
- Enter/Espaço seleciona card; filtros e paginação são botões nativos.
- Troca de página por teclado foca o primeiro card após a resposta. Refresh não rouba foco.
- Após remoção por snooze/outcome, focar o próximo card; se não houver, o anterior; se a lista esvaziar, o heading do empty state.
- O input de data possui label, formato esperado e mensagem de validação ligada por `aria-describedby`.

### Visual access

- Manter o outline global azul de 2px e offset de 2px; não remover `focus-visible`.
- Garantir contraste mínimo WCAG AA para texto e controles nos tokens dark existentes.
- Warning, danger, success e unknown sempre combinam texto + cor; ícones decorativos usam `aria-hidden="true"`.
- Respeitar `prefers-reduced-motion`; busy indicators não podem depender de animação para comunicar estado.
- Textos de 12px ficam restritos a metadados; instruções, erros e CTAs usam 14px ou mais.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | Nenhum | Não inicializado; decisão locked de preservar componentes Cordex existentes |
| Cordex local (`ui`, `ui2`) | `Button`, `Input`, `Badge`, `Pagination`, `Skeleton`, `EmptyState`, `SkeletonList`, `Textarea` | Fonte local inspecionada em 2026-07-13; sem registry externo, `eval`, import remoto ou acesso novo a secrets |
| Third-party registries | Nenhum | Não aplicável |

---

## Scope Guardrails for Executor

- Não tocar na lista completa legada nem nos componentes `src/components/tasks/*` para atender este contrato.
- Não transformar `WorkQueueItem` em novo ledger nem introduzir novo design system.
- Não esconder truncamento ou unknown atrás de toast temporário.
- Não inferir permissão, frescor ou bloqueio no frontend; renderizar a decisão explícita do contrato da API.
- Não ampliar nem refatorar efeitos externos nesta fase.
- Validar o mesmo runner sob `/tasks` e `/ai/triage`, incluindo mobile, teclado, contagens, paginação, stale e snooze.

---

## Upstream Decision Traceability

| Source | Decisions represented |
|--------|-----------------------|
| `10-CONTEXT.md` | Runner compartilhado, staff-first, busca remota, contagem honesta, CTA canônico, stale/unknown, snooze, acessibilidade e ausência de redesign |
| `10-PRD.md` | Alcance além de 25, total honesto, reuso, frescor e regressão das duas superfícies; hardening estrutural separado |
| `specs/054-work-queue-integrity-p0/spec.md` | Truncamento explícito, navegação completa, task canônica e critérios de aceite do slice sem migration |
| `10-RESEARCH.md` | Stack sem dependência nova, envelope/counts/truncated sources, paginação remota, readiness fields e waves estruturais |
| Código Cordex atual | Tokens, grid, componentes, copy base e padrões de loading/paginação existentes |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-07-13
