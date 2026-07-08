# DESIGN-SPEC — funnel-api

> Stack real (EMPRESA.md): FastAPI + SQLAlchemy 2.0 + Pydantic. Tenant scoping automático
> via sessão. Sem migração de banco: só leitura de tabelas existentes.

## Endpoint `GET /api/cockpit/weekly-funnel`

- **Router:** `saas-backend/app/routers/commercial_funnel.py`
  ```python
  router = APIRouter(prefix="/cockpit", tags=["cockpit"])

  @router.get("/weekly-funnel", response_model=WeeklyFunnelResponse)
  def weekly_funnel(
      db: Annotated[Session, Depends(get_db)],
      _: Annotated[User, Depends(require_roles(
          RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON, RoleEnum.RECEPTIONIST
      ))],
      week_offset: int = Query(0, ge=-12, le=0),
  ) -> WeeklyFunnelResponse:
      return get_weekly_funnel(db, week_offset=week_offset)
  ```
  (prefixo `/cockpit` compartilhado com `daily_cockpit.py` é intencional — paths distintos,
  routers separados, sem conflito FastAPI)

- **Schemas:** `saas-backend/app/schemas/commercial_funnel.py`
  ```python
  class FunnelStage(BaseModel):
      key: str              # "contacts" | "responses" | "conversions"
      label: str            # "Contatos feitos" | "Respostas recebidas" | "Conversões"
      value: int
      previous_value: int   # mesma métrica na semana anterior

  class ConversionBreakdown(BaseModel):
      leads_won: int        # vendas fechadas
      members_joined: int   # novos alunos
      risk_recovered: int   # alunos recuperados (saíram de red/yellow pra green)

  class WeeklyFunnelResponse(BaseModel):
      week_start: datetime  # segunda 00:00, fuso America/Sao_Paulo (aware, UTC no JSON)
      week_end: datetime    # min(now, domingo 23:59:59)
      week_offset: int
      contacts: FunnelStage
      responses: FunnelStage
      conversions: FunnelStage
      conversion_breakdown: ConversionBreakdown
  ```

- **Service:** `saas-backend/app/services/commercial_funnel_service.py`
  ```python
  def get_weekly_funnel(db: Session, *, week_offset: int = 0) -> WeeklyFunnelResponse: ...
  def _week_window(now: datetime, week_offset: int) -> tuple[datetime, datetime]: ...
  def _count_contacts(db: Session, start: datetime, end: datetime) -> int: ...
  def _count_responses(db: Session, start: datetime, end: datetime) -> int: ...
  def _count_conversions(db: Session, start: datetime, end: datetime) -> ConversionBreakdown: ...
  ```
  **Fontes pinadas (só dados que existem):**
  - `contacts` = `MessageLog` com `created_at` na janela, `direction != 'inbound'`
    (inclui NULL — legado é outbound) e `status != 'failed'`
    **+** `Task` com `status == DONE`, `completed_at` na janela e (`member_id` OU `lead_id`
    preenchido) — tarefa concluída direcionada a alguém é um contato da equipe.
  - `responses` = `MessageLog` com `created_at` na janela e `direction == 'inbound'`.
  - `conversions`:
    - `leads_won` = `Lead` com `deleted_at IS NULL`, `stage == WON`, `updated_at` na janela
      (proxy documentado: Lead não tem `converted_at`).
    - `members_joined` = `Member` com `deleted_at IS NULL` e `join_date` na janela.
    - `risk_recovered` = membros cujo registro mais recente de `MemberRiskHistory`
      (`recorded_at` na janela) tem `level == 'green'` E cujo registro imediatamente
      anterior era `red`/`yellow`. Contar membro no máximo 1×.
  - `previous_value` de cada estágio = mesma conta na janela `week_offset - 1`.
  - Semana vazia → todos os campos 0 (nunca 404/null).
  - **Sem cache** e sem `include_all_tenants`.

- **Auth/erros:** idênticos ao cockpit-api (`require_roles` existente; 422 automático do
  FastAPI pra `week_offset` fora de [-12, 0]).

## Smoke
`saas-backend/tests/test_commercial_funnel_service.py` — padrão de fixtures de
`tests/test_dashboard_service.py`. Casos mínimos:
1. Janela: `_week_window` retorna segunda 00:00 (São Paulo) e respeita `week_offset=-1`.
2. MessageLog outbound + task DONE com member_id contam em `contacts`; inbound conta só
   em `responses`; `status='failed'` não conta.
3. Lead WON na janela → `leads_won=1`; member com `join_date` na janela → `members_joined=1`.
4. Histórico red→green na janela → `risk_recovered=1`; green→green não conta; membro com
   duas transições conta 1×.
5. Semana sem dados → todos zero, 200 OK.
6. Isolamento de tenant (padrão guardrails).

Comando: `py -3.12 -m pytest saas-backend -q` (verde completo).

## Território
- `saas-backend/app/services/commercial_funnel_service.py`
- `saas-backend/app/schemas/commercial_funnel.py`
- `saas-backend/app/routers/commercial_funnel.py`
- `saas-backend/tests/test_commercial_funnel_service.py`

**Neutro proibido:** `app/routers/__init__.py`, `app/main.py` (reconciler registra),
`app/schemas/__init__.py`, `app/models/**`, `app/core/**`, migrations, CI.
