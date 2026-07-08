# CONTRACT — cockpit-api

## I/O
- **Input:** `GET /api/cockpit/daily` — sem parâmetros; JWT obrigatório; roles
  OWNER | MANAGER | SALESPERSON | RECEPTIONIST.
- **Output:** `DailyCockpitResponse` (shape exato na DESIGN-SPEC). Campos snake_case.
  Listas capadas em 10 itens; `counts.*` traz os totais. `triage_pending_count` inteiro ≥ 0.
  Tenant: dados exclusivamente do gym do usuário autenticado (guard de sessão).

Exemplo:
```json
{
  "generated_at": "2026-07-08T12:00:00Z",
  "leads_followup": [{"lead_id": "…", "full_name": "…", "phone": "…", "stage": "contact",
    "days_since_contact": 3, "reason": "Sem contato há 3 dias", "href": "/crm"}],
  "members_attention": [{"member_id": "…", "full_name": "…", "risk_level": "red",
    "retention_stage": "recovery", "days_without_checkin": 12,
    "reason": "12 dias sem treinar · estágio recuperação", "href": "/dashboard/retention"}],
  "actions_today": [{"task_id": "…", "title": "…", "priority": "high",
    "due_date": "2026-07-08T18:00:00Z", "overdue": false, "target_name": "…", "href": "/tasks"}],
  "triage_pending_count": 4,
  "counts": {"leads_followup": 17, "members_attention": 23, "actions_today": 6}
}
```

## Smoke (gate pra done)
```
py -3.12 -m pytest saas-backend -q
```
Suíte completa verde (1075 testes pré-existentes + os novos deste slot).

## Pendências pro reconciler
1. Registrar o router: import + include de `daily_cockpit.router` seguindo exatamente o
   padrão dos routers existentes (`app/routers/__init__.py` e/ou `app/main.py` — onde os
   demais são registrados).
2. Conferir critério de "pendente" da Central Cordex usado em `_triage_pending_count`
   contra o router `ai_triage.py` (fidelidade semântica).
