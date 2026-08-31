from unittest.mock import MagicMock

from app.core.dependencies import get_current_user
from app.database import get_db
from app.schemas import ImportErrorEntry, ImportPreview, ImportSummary


def _blocked_preview() -> ImportPreview:
    return ImportPreview(
        preview_kind="checkins",
        total_rows=2,
        valid_rows=1,
        would_create=1,
        can_confirm=False,
        blocking_issues=["Existe uma linha com erro."],
        errors=[
            ImportErrorEntry(
                row_number=3,
                reason="Formato de data invalido",
                payload={"cliente": "[redacted]"},
            )
        ],
    )


def _valid_preview() -> ImportPreview:
    return ImportPreview(
        preview_kind="checkins",
        total_rows=1,
        valid_rows=1,
        would_create=1,
        can_confirm=True,
    )


def test_checkin_commit_is_fail_closed_when_preflight_has_errors(app, client, mock_owner, monkeypatch):
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: mock_owner
    import_mock = MagicMock()
    audit_calls: list[dict] = []

    monkeypatch.setattr("app.routers.imports.preview_checkins_csv", lambda *_args, **_kwargs: _blocked_preview())
    monkeypatch.setattr("app.routers.imports.import_checkins_csv", import_mock)
    monkeypatch.setattr(
        "app.routers.imports.log_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    try:
        response = client.post(
            "/api/v1/imports/checkins",
            files={"file": ("Acessos.csv", b"Cliente,Data Entrada\nEvelyn Casela,data-invalida", "text/csv")},
        )

        assert response.status_code == 422
        assert "nenhum check-in foi gravado" in response.json()["detail"].lower()
        import_mock.assert_not_called()
        db.commit.assert_called_once()
        assert audit_calls[0]["action"] == "import_checkins_csv_blocked"
        assert audit_calls[0]["details"]["error_rows"] == [3]
        assert "payload" not in audit_calls[0]["details"]
    finally:
        app.dependency_overrides.clear()


def test_checkin_preview_audits_error_metadata_without_row_payload(app, client, mock_owner, monkeypatch):
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: mock_owner
    audit_calls: list[dict] = []

    monkeypatch.setattr("app.routers.imports.preview_checkins_csv", lambda *_args, **_kwargs: _blocked_preview())
    monkeypatch.setattr(
        "app.routers.imports.log_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    try:
        response = client.post(
            "/api/v1/imports/checkins/preview",
            files={"file": ("Acessos.csv", b"Cliente,Data Entrada\nEvelyn Casela,data-invalida", "text/csv")},
        )

        assert response.status_code == 200
        assert response.json()["can_confirm"] is False
        db.commit.assert_called_once()
        assert audit_calls[0]["action"] == "preview_checkins_csv_errors"
        assert audit_calls[0]["details"]["error_reasons"] == {"Formato de data invalido": 1}
        assert audit_calls[0]["details"]["file_sha256"]
        assert "payload" not in audit_calls[0]["details"]
    finally:
        app.dependency_overrides.clear()


def test_checkin_commit_runs_after_clean_preflight(app, client, mock_owner, monkeypatch):
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: mock_owner
    import_mock = MagicMock(
        return_value=ImportSummary(
            imported=1,
            skipped_duplicates=0,
        )
    )
    audit_calls: list[dict] = []

    monkeypatch.setattr("app.routers.imports.preview_checkins_csv", lambda *_args, **_kwargs: _valid_preview())
    monkeypatch.setattr("app.routers.imports.import_checkins_csv", import_mock)
    monkeypatch.setattr(
        "app.routers.imports.log_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    try:
        response = client.post(
            "/api/v1/imports/checkins",
            files={
                "file": (
                    "Acessos.csv",
                    b"Cliente,Data Entrada,Hora Entrada\nEvelyn Casela,27/08/2026,11:43",
                    "text/csv",
                )
            },
        )

        assert response.status_code == 200
        assert response.json()["imported"] == 1
        import_mock.assert_called_once()
        assert audit_calls[0]["action"] == "import_checkins_csv"
        db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()
