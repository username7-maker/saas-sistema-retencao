from app.core.config import Settings


def test_parse_cors_origins_accepts_json_list():
    raw = '["https://app.aigymos.com","https://admin.aigymos.com"]'
    parsed = Settings.parse_cors_origins(raw)  # type: ignore[arg-type]
    assert parsed == ["https://app.aigymos.com", "https://admin.aigymos.com"]


def test_parse_cors_origins_accepts_csv():
    raw = "https://app.aigymos.com, https://admin.aigymos.com"
    parsed = Settings.parse_cors_origins(raw)  # type: ignore[arg-type]
    assert parsed == ["https://app.aigymos.com", "https://admin.aigymos.com"]
