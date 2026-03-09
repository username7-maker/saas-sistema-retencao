from pydantic import BaseModel, Field


class ImportErrorEntry(BaseModel):
    row_number: int
    reason: str
    payload: dict


class MissingMemberEntry(BaseModel):
    name: str
    occurrences: int
    sample_plan: str | None = None


class ImportSummary(BaseModel):
    imported: int
    skipped_duplicates: int
    ignored_rows: int = 0
    provisional_members_created: int = 0
    provisional_members: list[str] = Field(default_factory=list)
    missing_members: list[MissingMemberEntry] = Field(default_factory=list)
    errors: list[ImportErrorEntry]
