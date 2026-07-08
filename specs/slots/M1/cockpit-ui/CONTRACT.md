# CONTRACT — cockpit-ui

## I/O
- **Input (dados):** `GET /api/cockpit/daily` e `GET /api/cockpit/weekly-funnel` —
  shapes pinados nos CONTRACTs de `cockpit-api` e `funnel-api` (fonte da verdade;
  `src/types/cockpit.ts` é espelho literal).
- **Output (UI):** bloco "Hoje" no topo de `/dashboard/executive` com 4 painéis
  (Follow-ups de leads · Alunos em atenção · Ações do dia · Funil da semana), estados
  vazio/carregando/erro/sucesso por painel, deep-link por item (`href` do payload).
- O conteúdo atual do Dashboard Executivo permanece intacto abaixo do bloco.

## Smoke (gate pra done)
```
cd saas-frontend && npm run build
py -3.12 -m pytest saas-backend -q
```
Ambos verdes.

## Pendências pro reconciler
1. Integração real com os endpoints (os dois slots de API mergeiam junto): abrir
   `/dashboard/executive` com backend rodando e conferir os 4 painéis com dado real.
2. Se a assinatura do client `api` divergir do assumido no hook (ver DESIGN-SPEC),
   validar que o worker seguiu o padrão real de `dashboardService.ts`.
3. Acesso por papel: endpoints aceitam SALESPERSON/RECEPTIONIST, mas a rota
   `/dashboard/executive` hoje é restrita a OWNER/MANAGER no frontend — decisão de
   ampliar acesso da página é do CTO no fechamento do M1 (registrar em ADR se mudar).
