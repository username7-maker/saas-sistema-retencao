# ROADMAP — Cordex Gym OS

> Fonte da verdade do escopo por milestone. Método: `specs/PARALLEL-PROTOCOL.md`.
> Histórico pré-método: specs `001`–`052` (entregues; ver `specs/`).

## M1 — Cockpit Comercial Diário  (status: em andamento — iniciado 2026-07-08)

**Objetivo:** a equipe da ProGym abre o Dashboard Executivo de manhã e sabe, sem planilha
paralela: (1) quais leads precisam de resposta/follow-up, (2) quais alunos estão em risco
de churn ou janela de renovação, (3) quais ações devem ser feitas hoje, e (4) qual foi o
resultado comercial da semana (esforço → resultado). Cada item leva em 1 clique pra tela
de execução que já existe (CRM, fila de retenção, tarefas, Central Cordex).

**Decisões do fundador (2026-07-08):**
- Evoluir o **Dashboard Executivo** existente (não criar tela nova).
- Foco **desktop da recepção**; mobile utilizável, não prioritário.
- Resultado = **funil esforço→resultado**: contatos feitos → respostas → conversões
  (venda, renovação, reativação) na semana. Sem R$ atribuído neste milestone.
- Prazo alvo: piloto utilizável na ProGym em 2–3 semanas.

**Critérios de sucesso (HTC — o que a pessoa testa):**
1. Abrir `/dashboard/executive` e ver o bloco "Hoje" com 4 painéis preenchidos com dados
   reais: Follow-ups de leads · Alunos em atenção · Ações do dia · Funil da semana.
2. Clicar num lead do painel de follow-ups → cair no lead certo no CRM.
3. Clicar num aluno em atenção → cair na rotina de retenção daquele aluno.
4. Concluir uma ação do dia na tela de destino → ela sai do cockpit ao recarregar.
5. O funil da semana mostra contatos → respostas → conversões coerentes com a operação.
6. A equipe consegue rodar a rotina da manhã inteira sem abrir planilha.

**Slots (territórios disjuntos — specs/slots/M1/):**
- `cockpit-api` — endpoint agregado "rotina do dia" (3 listas com deep-link) —
  território `saas-backend/app/{services,schemas,routers}/daily_cockpit*` + teste
- `funnel-api` — endpoint "funil semanal esforço→resultado" sobre MessageLog/TaskEvent/
  Lead/Member — território `saas-backend/app/{services,schemas,routers}/commercial_funnel*` + teste
- `cockpit-ui` — bloco "Hoje" no Dashboard Executivo consumindo os 2 endpoints —
  território `DashboardLovable.tsx`, `dashboardAdapters.ts`, `src/components/dashboard/cockpit/**`,
  `src/hooks/useCockpit.ts`, `src/types/cockpit.ts`

Registro na numeração viva: **spec 053** (`specs/053-daily-commercial-cockpit/`).

## M2+ (esboço — não iniciar sem fechar M1 no HTC)

- **Resposta rastreada por canal** — threading Kommo/WhatsApp pra medir resposta por
  conversa (hoje: inbound agregado do MessageLog).
- **R$ no funil** — valor recuperado/renovado atribuído às ações (depende de dado
  financeiro confiável no piloto).
- **Cockpit mobile** — rotina 100% no celular pra equipe que circula na academia.
- **Planner de campanhas** — agendar campanhas/ações recorrentes a partir do Growth OS.
- **Multi-unidade** — cockpit consolidado pra redes (2ª academia da Cordex).
