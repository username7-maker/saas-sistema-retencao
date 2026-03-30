from pydantic import BaseModel, Field


class ImportErrorEntry(BaseModel):
    row_number: int
    reason: str
    payload: dict


class MissingMemberEntry(BaseModel):
    name: str
    occurrences: int
    sample_plan: str | None = None


class ImportMappingOption(BaseModel):
    value: str
    label: str
    required: bool = False


class ImportSummary(BaseModel):
    imported: int
    skipped_duplicates: int
    ignored_rows: int = 0
    provisional_members_created: int = 0
    provisional_members: list[str] = Field(default_factory=list)
    missing_members: list[MissingMemberEntry] = Field(default_factory=list)
    errors: list[ImportErrorEntry] = Field(default_factory=list)


class ImportPreviewRow(BaseModel):
    row_number: int
    action: str
    preview: dict


class ImportPreview(BaseModel):
    preview_kind: str
    total_rows: int
    valid_rows: int
    would_create: int = 0
    would_update: int = 0
    would_skip: int = 0
    ignored_rows: int = 0
    provisional_members_possible: int = 0
    recognized_columns: list[str] = Field(default_factory=list)
    unrecognized_columns: list[str] = Field(default_factory=list)
    detected_columns: list[str] = Field(default_factory=list)
    suggested_mapping: dict[str, str | None] = Field(default_factory=dict)
    mapping_options: list[ImportMappingOption] = Field(default_factory=list)
    missing_required_fields: list[str] = Field(default_factory=list)
    duplicate_target_fields: list[str] = Field(default_factory=list)
    mapping_ready: bool = True
    missing_members: list[MissingMemberEntry] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    sample_rows: list[ImportPreviewRow] = Field(default_factory=list)
    errors: list[ImportErrorEntry] = Field(default_factory=list)
