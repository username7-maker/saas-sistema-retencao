from pydantic import BaseModel


class ImportErrorEntry(BaseModel):
    row_number: int
    reason: str
    payload: dict


class ImportSummary(BaseModel):
    imported: int
    skipped_duplicates: int
    errors: list[ImportErrorEntry]
