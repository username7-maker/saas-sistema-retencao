# Spec 036 - Cordex Command Center Premium Frontend

## User Story
Como gestor de academia, quero abrir o Cordex Gym OS e sentir que estou em um centro de comando premium, com decisões, riscos e ações claras, sem perder os fluxos operacionais já existentes.

## Requirements
- O design system deve suportar o padrão dark enterprise premium.
- O App Shell deve preservar RBAC, rotas, logout, notificações e busca.
- O dashboard executivo deve usar dados reais dos hooks existentes.
- Dashboards operacional, comercial, financeiro e retenção devem usar a mesma linguagem visual.
- Empty states devem explicar lacunas de dados sem inventar números.
- Nenhum contrato backend pode mudar nesta fase.

## Non-Goals
- Redesign profundo de todas as páginas operacionais.
- Mudança de backend.
- Novo pacote pesado de UI ou gráficos.
- Dados mockados em produção.

## Acceptance Criteria
- Componentes premium estão em `src/components/ui2/command`.
- `LovableLayout` usa a linguagem Cordex Command Center.
- `DashboardLovable` exibe hero, KPIs, mapa, briefing, gráficos e matriz de risco.
- `npm run build` passa.
