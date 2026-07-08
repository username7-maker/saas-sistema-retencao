# DESIGN-OVERVIEW — Cordex Gym OS

> **Fonte de verdade visual:** o produto em produção (Cordex Design System v1, spec 030).
> `docs/design/raw/` está vazio de propósito — decisão do fundador (2026-07-08): construir
> sobre o design existente. Cada tela referencia o **código-fonte** em `saas-frontend/src/`,
> que aqui cumpre o papel do export.

## Tokens

Definidos em `saas-frontend/tailwind.config.js` + `saas-frontend/src/styles/lovable-theme.css`.
Dois temas (claro/escuro via classe `dark`), consumidos como `lovable-*` no Tailwind.

- **Cores (tema escuro — o principal, "Dark Intelligence"):**
  - Fundo em camadas: `layer-base #0A0B0F`, `layer-surface #0E1018`, `layer-elevated #101320`, sidebar `#0C0E14`
  - Superfícies lovable: bg `hsl(228 15% 6%)`, surface `hsl(228 20% 8%)`, border `hsl(228 8% 14%)`
  - Texto: ink `hsl(220 10% 96%)`, muted `hsl(220 10% 55%)`
  - Primária: azul `hsl(217 91% 60%)` (~`#3b82f6`); acentos command: cyan `#00c8ff`, purple `#8b5cf6`
  - Semânticas: success `hsl(158 64% 42%)`, warning `hsl(38 92% 50%)`, danger `hsl(0 100% 61%)`, **IA = violeta `hsl(258 90% 66%)`**
  - Status operacionais (`pi-*`): green `#22c55e`, red `#ff3b30`, cyan `#00c8ff`, orange `#f97316`
- **Tema claro:** bg `hsl(210 24% 96%)`, surface creme `hsl(42 28% 97%)`, primária ciano-azul `hsl(199 89% 48%)`.
- **Tipografia:** UI/corpo `Inter` (fallback Barlow); títulos/display `Barlow Condensed` (fallback Space Grotesk); mono `JetBrains Mono`. Headlines grandes: `text-5xl/6xl font-extrabold tracking-tight`.
- **Estilo:** sombras `shadow-card` (sutil + inset highlight) e glows coloridos por semântica (`glow-blue/violet/danger/green/red/cyan/orange`); animações `rise` (entrada 0.45s), `pulse-glow`, `pi-pulse` (alerta). Densidade confortável, cantos arredondados médios.
- **Componentes canônicos:** `src/components/ui2/` (Button, Card, Table, Tabs, Drawer, Dialog, Badge, Select…) e `src/components/ui2/command/` (MetricCard, CommandCard, ActionQueue, RiskMatrix, PremiumTable, StatusPill, AIInsightPanel, PremiumEmptyState/Skeleton). **Tela nova usa esses componentes — não criar variantes paralelas.**

## Navegação (layout `LovableLayout.tsx`)

Sidebar fixa (272px, desktop) em 4 grupos + header com notificações, perfil e logout.
Papel `professor` vê menu reduzido ("Treino"). Grupos:

1. **Dashboards** — Executivo, Operacional, Comercial, Financeiro, Retenção
2. **Gestão** — Membros, Avaliações, Method OS, CRM, Central Cordex, Revisão Cordex, Tarefas
3. **Resultados** — Metas, NPS, Relatórios
4. **Sistema** — Cordex Autopilot, Importações, Auditoria

## Telas relevantes pro milestone (cockpit comercial diário)

### Dashboard Executivo (ref: `src/pages/dashboard/DashboardLovable.tsx`)
- Propósito: visão geral "Mapa de Inteligência Operacional" — como indicadores se conectam pra proteger frequência, retenção e receita.
- Componentes: headline display, MetricCards, **Fila de ações sugeridas** (ActionQueue), gráficos Churn/NPS, **Matriz de risco** (RiskMatrix).
- Estados: vazio ("Nenhuma ação urgente", "Base operacional ainda insuficiente"), skeleton premium, erro.

### Dashboard Retenção (ref: `src/pages/dashboard/RetentionDashboardPage.tsx`)
- Propósito: fila operacional de risco — quem está escapando e o que fazer.
- Componentes: **Copiloto de retenção** (explicação curta + canal sugerido + abordagem por aluno), Sinais captados, Playbook sugerido, Fila operacional com busca/paginação.
- Estados: erro de carga, "Nenhum alerta encontrado".

### CRM (ref: `src/pages/crm/CrmPage.tsx` + `src/components/crm/PipelineKanban.tsx`)
- Propósito: funil comercial. Três blocos: **Acquisition OS** (origem, qualificação e próxima ação na captura), **Pipeline Kanban** (estágios + valor estimado), **Growth OS** (audiências acionáveis: conversão, reativação, renovação, NPS, indicação).
- Ações → leva a: Briefing de venda (`/vendas/briefing/:leadId`) e Script de ligação (`/vendas/script/:leadId`, com registro de próximo passo).
- Estados: erro, "Nenhum lead encontrado", "Growth OS indisponível".

### Central Cordex (ref: `src/pages/ai/AITriageInboxPage.tsx`)
- Propósito: execução guiada — "abra o item, prepare a ação indicada, use a mensagem pronta e registre o resultado".
- Componentes: fila de triagem IA com mensagens prontas (IA sugere, humano aprova).

### Tarefas (ref: `src/pages/tasks/TasksPage.tsx`)
- Propósito: **modo execução operacional** — fila do dia sem retenção misturada (botão dedicado pra retenção), subfiltros, foco (TasksFocusSection), detalhe em drawer.
- Estados: onboarding tab, vazio, erro.

### Apoio: Membros (lista + drawers + Perfil 360 com "Decisão operacional"), NPS, Relatórios (disparo mensal), Metas, Cordex Autopilot (automações), Auditoria.

## Fluxos principais (hoje)

1. **Retenção:** Dashboard Retenção → fila → Copiloto (canal + abordagem) → executa → registra.
2. **Comercial:** CRM → lead no Kanban → Briefing/Script → registra próximo passo.
3. **Execução:** Central Cordex ou Tarefas → item → mensagem pronta → resultado.

## Perguntas em aberto (pro fundador)

1. O "cockpit diário" deve ser uma **tela nova** (página inicial da rotina) ou a evolução do Dashboard Executivo existente?
2. A equipe opera hoje mais no desktop da recepção ou também no celular? (define prioridade de responsividade)
3. "Resultado comercial básico" = o quê, na sua cabeça? (ex.: contatos feitos → respostas → renovações/vendas fechadas na semana)
