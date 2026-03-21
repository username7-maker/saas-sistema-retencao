from pydantic import BaseModel, Field


class AIAssistantPayload(BaseModel):
    summary: str
    why_it_matters: str
    next_best_action: str
    suggested_message: str | None = None
    evidence: list[str] = Field(default_factory=list)
    confidence_label: str = "Inicial"
    recommended_channel: str = "context"
    cta_target: str = "/"
    cta_label: str = "Abrir contexto"
