BODY_COMPOSITION_SOURCES = (
    "tezewa",
    "manual",
    "ocr_receipt",
    "device_import",
    "actuar_sync",
)

ACTUAR_SYNC_MODES = (
    "disabled",
    "http_api",
    "csv_export",
    "assisted_rpa",
    "local_bridge",
)

ACTUAR_SYNC_STATUSES = (
    "draft",
    "saved",
    "sync_pending",
    "syncing",
    "synced_to_actuar",
    "sync_failed",
    "needs_review",
    "manual_sync_required",
)

ACTUAR_SYNC_TERMINAL_STATUSES = frozenset(
    {
        "saved",
        "synced_to_actuar",
        "needs_review",
        "manual_sync_required",
    }
)

ACTUAR_SYNC_ATTEMPT_STATUSES = (
    "pending",
    "processing",
    "exported",
    "synced",
    "failed",
    "skipped",
    "disabled",
)

ACTUAR_SYNC_JOB_TYPES = (
    "body_composition_push",
)

ACTUAR_SYNC_JOB_STATUSES = (
    "pending",
    "processing",
    "synced",
    "failed",
    "needs_review",
    "cancelled",
)

ACTUAR_SYNC_ATTEMPT_V2_STATUSES = (
    "started",
    "succeeded",
    "failed",
)

ACTUAR_BRIDGE_DEVICE_STATUSES = (
    "pairing",
    "online",
    "offline",
    "revoked",
)

ACTUAR_FIELD_CLASSIFICATIONS = (
    "critical_direct",
    "critical_derived",
    "non_critical_direct",
    "unsupported",
    "text_note_only",
)

OCR_WARNING_SEVERITIES = (
    "warning",
    "critical",
)
