# DESIGN-SPEC — cockpit-api

> Stack real (EMPRESA.md): FastAPI + SQLAlchemy 2.0 + Pydantic. Fronteira validada com
> Pydantic (equivalente ao "Zod nas fronteiras" do STACK-DEFAULT). Tenant scoping é
> automático via sessão (`app/database.py` ContextVar — spec 001); NÃO usar
> `include_all_tenants`.

## Endpoint `GET /api/cockpit/daily`

- **Router:** `saas-backend/app/routers/daily_cockpit.py`
  ```python
  router = APIRouter(prefix="/cockpit", tags=["cockpit"])

  @router.get("/daily", response_model=DailyCockpitResponse)
  def daily_cockpit(
      db: Annotated[Session, Depends(get_db)],
      _: Annotated[User, Depends(require_roles(
          RoleEnum.OWNER, RoleEnum.MANAGER, RoleEnum.SALESPERSON, RoleEnum.RECEPTIONIST
      ))],
  ) -> DailyCockpitResponse:
      return get_daily_cockpit(db)
  ```
  (padrão idêntico a `app/routers/dashboards.py`; import de schema direto do módulo,
  como `from app.schemas.insights import InsightResponse` faz — NÃO editar barrel)

- **Schemas:** `saas-backend/app/schemas/daily_cockpit.py` (Pydantic `BaseModel`, nomes exatos)
  ```python
  class CockpitLeadFollowup(BaseModel):
      lead_id: UUID
      full_name: str
      phone: str | None
      stage: str                      # valor do LeadStage
      days_since_contact: int | None  # None = nunca contatado
      reason: str                     # ex.: "Sem contato há 3 dias" / "Nunca contatado"
      href: str                       # "/crm"

  class CockpitMemberAttention(BaseModel):
      member_id: UUID
      full_name: str
      risk_level: str                 # "red" | "yellow"
      retention_stage: str | None     # valores de retention_stage_service
      days_without_checkin: int | None
      reason: str                     # ex.: "12 dias sem treinar · estágio recuperação"
      href: str                       # "/dashboard/retention"

  class CockpitActionToday(BaseModel):
      task_id: UUID
      title: str
      priority: str                   # valor do TaskPriority
      due_date: datetime | None
      overdue: bool
      target_name: str | None         # nome do membro ou lead vinculado
      href: str                       # "/tasks"

  class CockpitCounts(BaseModel):
      leads_followup: int             # total (a lista vem capada em 10)
      members_attention: int
      actions_today: int

  class DailyCockpitResponse(BaseModel):
      generated_at: datetime
      leads_followup: list[CockpitLeadFollowup]
      members_attention: list[CockpitMemberAttention]
      actions_today: list[CockpitActionToday]
      triage_pending_count: int       # itens pendentes da Central Cordex
      counts: CockpitCounts
  ```

- **Service:** `saas-backend/app/services/daily_cockpit_service.py`
  ```python
  FOLLOWUP_STALE_HOURS = 48
  OPEN_LEAD_STAGES = (LeadStage.NEW, LeadStage.CONTACT, LeadStage.VISIT, LeadStage.TRIAL,
                      LeadStage.PROPOSAL, LeadStage.MEETING_SCHEDULED, LeadStage.PROPOSAL_SENT)
  LIST_CAP = 10

  def get_daily_cockpit(db: Session) -> DailyCockpitResponse: ...
  def _leads_needing_followup(db: Session, now: datetime) -> tuple[list[CockpitLeadFollowup], int]: ...
  def _members_attention(db: Session, now: datetime) -> tuple[list[CockpitMemberAttention], int]: ...
  def _actions_today(db: Session, now: datetime) -> tuple[list[CockpitActionToday], int]: ...
  def _triage_pending_count(db: Session) -> int: ...
  ```
  **Regras de dados (fontes reais, sem migração):**
  - `_leads_needing_followup`: `Lead` com `deleted_at IS NULL`, `stage IN OPEN_LEAD_STAGES`
    e (`last_contact_at IS NULL` OU `last_contact_at < now - 48h`). Ordena:
    `last_contact_at ASC NULLS FIRST`. Retorna (top 10, total).
  - `_members_attention`: `Member` com `deleted_at IS NULL`, `status == ACTIVE`,
    `risk_level IN (RED, YELLOW)`. Ordena: RED primeiro, depois `risk_score DESC`.
    `days_without_checkin` derivado de `last_checkin_at`. Sem duplicar aluno.
  - `_actions_today`: `Task` com `status IN (TODO, DOING)` e `due_date <= hoje 23:59`
    (fuso America/Sao_Paulo); `overdue = due_date < now`. Ordena: overdue primeiro,
    depois prioridade (URGENT > HIGH > MEDIUM > LOW), depois `due_date ASC`.
    `target_name` via relacionamento member/lead (join, sem N+1).
  - `_triage_pending_count`: count de `AITriageRecommendation` pendente (usar o mesmo
    critério de "pendente" do router `ai_triage.py` — ler antes de implementar).
  - **Sem cache** (diferente dos dashboards): cockpit é operacional, dado fresco.
  - LGPD: payload só com nome/telefone (padrão já usado no `RetentionQueueItem`). Nada de
    CPF, e-mail só se o CRM já expõe.

- **Auth:** roles OWNER, MANAGER, SALESPERSON, RECEPTIONIST (a recepção opera o cockpit).
- **Erros:** 401 sem token, 403 role não permitida (comportamento do `require_roles`
  existente — sem código novo).

## Smoke
`saas-backend/tests/test_daily_cockpit_service.py` — seguir o padrão de fixtures de
`tests/test_dashboard_service.py`. Casos mínimos:
1. Lead sem contato há 3 dias aparece em `leads_followup` com reason correta; lead WON não aparece.
2. Membro RED ativo aparece antes de YELLOW; membro cancelado não aparece.
3. Task vencida ontem vem com `overdue=True` antes de task de hoje; task DONE não aparece.
4. Listas capadas em 10 com `counts` refletindo o total real.
5. Isolamento de tenant: dado de outro gym não vaza (padrão dos testes de guardrails).

Comando: `py -3.12 -m pytest saas-backend -q` (verde completo).

## Território
- `saas-backend/app/services/daily_cockpit_service.py`
- `saas-backend/app/schemas/daily_cockpit.py`
- `saas-backend/app/routers/daily_cockpit.py`
- `saas-backend/tests/test_daily_cockpit_service.py`

**Neutro proibido:** `app/routers/__init__.py`, `app/main.py` (reconciler registra o
router), `app/schemas/__init__.py`, `app/models/**`, `app/core/**`, migrations, CI.
