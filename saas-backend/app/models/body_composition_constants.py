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
)

ACTUAR_SYNC_STATUSES = (
    "disabled",
    "pending",
    "exported",
    "synced",
    "failed",
    "skipped",
)

ACTUAR_SYNC_TERMINAL_STATUSES = frozenset(
    {
        "synced",
        "exported",
        "disabled",
        "skipped",
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

OCR_WARNING_SEVERITIES = (
    "warning",
    "critical",
)
