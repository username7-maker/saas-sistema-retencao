# BRIEF — funnel-api

**O quê:** endpoint `GET /api/cockpit/weekly-funnel` com o funil comercial da semana:
**contatos feitos → respostas recebidas → conversões** (venda, renovação, reativação),
com comparação contra a semana anterior.

**Por quê:** é a 4ª pergunta do cockpit (M1): "o que rendeu?". O fundador definiu
resultado = funil esforço→resultado, sem R$ atribuído neste milestone.

**Critérios de aceite:**
- `GET /api/cockpit/weekly-funnel` autenticado responde 200 com o shape do CONTRACT.md,
  escopado por `gym_id` (tenant guard em toda query).
- Contatos = mensagens outbound do `MessageLog` + tarefas de contato concluídas
  (`TaskEvent`) na janela; respostas = `MessageLog` inbound na janela; conversões =
  leads que viraram aluno + renovações + reativações na janela (fontes exatas na
  DESIGN-SPEC, só com dados que já existem — sem migração).
- Janela padrão: segunda 00:00 → agora (fuso da academia); aceita `?week_offset=-1`
  pra semana anterior. Retorna também os totais da semana anterior pra comparação.
- Semana sem dados retorna zeros (não 404, não null).
- Smoke verde: `py -3.12 -m pytest saas-backend -q` (na worktree, com deps do 3.12).

**Território (pode editar):**
- `saas-backend/app/services/commercial_funnel_service.py` (novo)
- `saas-backend/app/schemas/commercial_funnel.py` (novo)
- `saas-backend/app/routers/commercial_funnel.py` (novo)
- `saas-backend/tests/test_commercial_funnel_service.py` (novo)

**Zonas neutras (NÃO tocar — reconciler faz):**
- `saas-backend/app/routers/__init__.py`, `saas-backend/app/main.py` (registro do router)
- `saas-backend/app/schemas/__init__.py`, `saas-backend/app/models/**`, `app/core/**`
- `requirements.txt`, migrations Alembic (sem mudança de schema), CI

**Depende de:** nada (paralelo). Reusa models existentes por import read-only.
