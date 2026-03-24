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
    errors: list[ImportErrorEntry] = Field(default_factory=list)


class ImportPreviewRow(BaseModel):
    row_number: int
    action: str
    preview: dict


class ImportPreviewSourceColumn(BaseModel):
    source_key: str
    source_label: str
    status: str
    suggested_target: str | None = None
    applied_target: str | None = None
    sample_values: list[str] = Field(default_factory=list)
    can_ignore: bool = True


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
    missing_members: list[MissingMemberEntry] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    sample_rows: list[ImportPreviewRow] = Field(default_factory=list)
    mapping_required: bool = False
    can_confirm: bool = True
    resolved_mappings: dict[str, str] = Field(default_factory=dict)
    ignored_columns: list[str] = Field(default_factory=list)
    conflicting_targets: list[str] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    source_columns: list[ImportPreviewSourceColumn] = Field(default_factory=list)
    errors: list[ImportErrorEntry] = Field(default_factory=list)
