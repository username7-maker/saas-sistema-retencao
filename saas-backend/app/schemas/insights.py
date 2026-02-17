from pydantic import BaseModel


class InsightResponse(BaseModel):
    dashboard: str
    insight: str
    source: str  # "ai" or "fallback"
