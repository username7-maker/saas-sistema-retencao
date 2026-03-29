from pydantic import BaseModel, Field


class RoiTopPlaybook(BaseModel):
    playbook_key: str
    actions_executed: int
    recovered_members: int
    estimated_preserved_revenue: float


class RoiTopChannel(BaseModel):
    channel: str
    actions_executed: int
    recovered_members: int
    estimated_preserved_revenue: float


class RoiTopOperator(BaseModel):
    user_id: str | None = None
    label: str
    actions_executed: int
    recovered_members: int
    estimated_preserved_revenue: float


class RoiSummaryOut(BaseModel):
    period_days: int
    labeling: str = "estimativa_operacional"
    actions_executed: int
    total_automated: int = 0
    reengaged_count: int
    reengagement_rate: float
    preserved_revenue: float
    recovery_rate: float
    top_playbooks: list[RoiTopPlaybook] = Field(default_factory=list)
    top_channels: list[RoiTopChannel] = Field(default_factory=list)
    top_operators: list[RoiTopOperator] = Field(default_factory=list)
    top_reengaged: list[dict] = Field(default_factory=list)
