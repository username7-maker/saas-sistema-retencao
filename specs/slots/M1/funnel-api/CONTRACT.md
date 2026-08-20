# CONTRACT — funnel-api

## I/O
- **Input:** `GET /api/cockpit/weekly-funnel?week_offset=0` — `week_offset` opcional,
  inteiro em [-12, 0] (0 = semana corrente). JWT obrigatório; roles OWNER | MANAGER |
  SALESPERSON | RECEPTIONIST.
- **Output:** `WeeklyFunnelResponse` (shape exato na DESIGN-SPEC). Semana sem dados = zeros.

Exemplo:
```json
{
  "week_start": "2026-07-06T03:00:00Z",
  "week_end": "2026-07-08T15:00:00Z",
  "week_offset": 0,
  "contacts":    {"key": "contacts",    "label": "Contatos feitos",      "value": 42, "previous_value": 35},
  "responses":   {"key": "responses",   "label": "Respostas recebidas",  "value": 18, "previous_value": 11},
  "conversions": {"key": "conversions", "label": "Conversões",           "value": 5,  "previous_value": 3},
  "conversion_breakdown": {"leads_won": 2, "members_joined": 2, "risk_recovered": 1}
}
```

## Definições de negócio (fonte da verdade pro frontend e pro HTC)
- **Contatos feitos** = mensagens enviadas pela academia (WhatsApp/e-mail) + tarefas
  concluídas direcionadas a aluno/lead, na semana.
- **Respostas recebidas** = mensagens inbound registradas na semana.
- **Conversões** = vendas fechadas (leads ganhos) + novos alunos + alunos recuperados
  (saíram do risco pro verde).
- **Renovação financeira (R$) NÃO entra no M1** — decisão do CTO em docs/ROADMAP.md; vai
  pro M2 quando houver dado financeiro confiável no piloto.

## Smoke (gate pra done)
```
py -3.12 -m pytest saas-backend -q
```
Suíte completa verde.

## Pendências pro reconciler
1. Registrar o router `commercial_funnel.router` no padrão dos existentes.
2. Validar com dado real da ProGym que `direction` NULL como outbound não infla `contacts`
   de forma absurda (se inflar, reabrir slot com regra refinada).
