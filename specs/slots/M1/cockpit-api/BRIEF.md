# BRIEF — cockpit-api

**O quê:** endpoint agregado `GET /api/cockpit/daily` que responde as 3 primeiras perguntas
da rotina da manhã: leads que precisam de follow-up, alunos em atenção (risco de churn /
janela de renovação) e ações do dia — cada item com deep-link pra tela de execução.

**Por quê:** é a fonte de dados do bloco "Hoje" do cockpit (M1). Hoje essas respostas
existem espalhadas em 5 endpoints/telas; a recepção precisa delas juntas, ordenadas por
urgência, em uma chamada.

**Critérios de aceite:**
- `GET /api/cockpit/daily` autenticado responde 200 com as 3 listas do CONTRACT.md,
  escopadas por `gym_id` do usuário (tenant guard em toda query).
- Leads de follow-up vêm ordenados por urgência (mais tempo sem resposta primeiro) e cada
  item diz o motivo em linguagem de operação (ex.: "sem contato há 3 dias").
- Alunos em atenção unificam risco (fila de retenção) e renovação, sem duplicar aluno.
- Ações do dia = tarefas abertas com vencimento até hoje + itens pendentes da Central
  Cordex; ação concluída na origem desaparece na chamada seguinte.
- Nenhum dado pessoal sensível no payload além do necessário pra operação (nome, telefone
  mascarado se houver esse padrão nos endpoints existentes — seguir o padrão do CRM).
- Smoke verde: `py -3.12 -m pytest saas-backend -q` (na worktree, com deps do 3.12).

**Território (pode editar):**
- `saas-backend/app/services/daily_cockpit_service.py` (novo)
- `saas-backend/app/schemas/daily_cockpit.py` (novo)
- `saas-backend/app/routers/daily_cockpit.py` (novo)
- `saas-backend/tests/test_daily_cockpit_service.py` (novo)

**Zonas neutras (NÃO tocar — reconciler faz):**
- `saas-backend/app/routers/__init__.py`, `saas-backend/app/main.py` (registro do router)
- `saas-backend/app/schemas/__init__.py`, `saas-backend/app/models/**`, `app/core/**`
- `requirements.txt`, migrations Alembic (este slot não muda schema de banco), CI

**Depende de:** nada (paralelo). Reusa services/models existentes só por import read-only.
