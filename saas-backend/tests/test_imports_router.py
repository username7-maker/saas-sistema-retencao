from unittest.mock import MagicMock

from app.core.dependencies import get_current_user
from app.database import get_db
from app.routers import imports as imports_router
from app.schemas import ImportErrorEntry, ImportPreview, ImportSummary


def _blocked_preview() -> ImportPreview:
    return ImportPreview(
        preview_kind="checkins",
        total_rows=2,
        valid_rows=1,
        would_create=1,
        can_confirm=True,
        warnings=["Uma linha sera mantida como pendencia."],
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


def _unconfirmable_preview() -> ImportPreview:
    return ImportPreview(
        preview_kind="checkins",
        total_rows=1,
        valid_rows=0,
        can_confirm=False,
        blocking_issues=["Nenhuma linha valida foi encontrada."],
        errors=[ImportErrorEntry(row_number=2, reason="Formato de data invalido", payload={})],
    )


def _blocked_member_access_preview() -> ImportPreview:
    return ImportPreview(
        preview_kind="members",
        total_rows=1,
        valid_rows=1,
        would_update=1,
        can_confirm=False,
        blocking_issues=[
            "Arquivo de acessos/catraca detectado. Envie este arquivo em Importar check-ins."
        ],
    )


def test_member_commit_blocks_access_export_before_any_write(app, client, mock_owner, monkeypatch):
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: mock_owner
    import_mock = MagicMock()
    audit_calls: list[dict] = []

    monkeypatch.setattr("app.routers.imports.preview_members_csv", lambda *_args, **_kwargs: _blocked_member_access_preview())
    monkeypatch.setattr("app.routers.imports.import_members_csv", import_mock)
    monkeypatch.setattr(
        "app.routers.imports.log_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    try:
        response = client.post(
            "/api/v1/imports/members",
            files={
                "file": (
                    "Acessos.csv",
                    b"Cliente,Data Entrada,Hora Entrada,Assinatura\nEvelyn Casela,27/08/2026,11:43,LIVRE MENSAL",
                    "text/csv",
                )
            },
        )

        assert response.status_code == 422
        assert "nenhum cadastro foi alterado" in response.json()["detail"].lower()
        import_mock.assert_not_called()
        db.commit.assert_called_once()
        assert audit_calls[0]["action"] == "import_members_csv_blocked"
        assert audit_calls[0]["details"]["would_update"] == 1
        assert "payload" not in audit_calls[0]["details"]
    finally:
        app.dependency_overrides.clear()


def test_member_preview_audits_access_export_block_without_payload(app, client, mock_owner, monkeypatch):
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: mock_owner
    audit_calls: list[dict] = []

    monkeypatch.setattr("app.routers.imports.preview_members_csv", lambda *_args, **_kwargs: _blocked_member_access_preview())
    monkeypatch.setattr(
        "app.routers.imports.log_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    try:
        response = client.post(
            "/api/v1/imports/members/preview",
            files={"file": ("Acessos.csv", b"Cliente,Data Entrada,Hora Entrada\nEvelyn,27/08/2026,11:43", "text/csv")},
        )

        assert response.status_code == 200
        assert response.json()["can_confirm"] is False
        db.commit.assert_called_once()
        assert audit_calls[0]["action"] == "preview_members_csv_blocked"
        assert "payload" not in audit_calls[0]["details"]
    finally:
        app.dependency_overrides.clear()


def test_checkin_commit_imports_valid_rows_and_returns_pending_rows(app, client, mock_owner, monkeypatch):
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: mock_owner
    import_mock = MagicMock(
        return_value=ImportSummary(
            imported=1,
            skipped_duplicates=0,
            errors=[
                ImportErrorEntry(
                    row_number=3,
                    reason="Formato de data invalido",
                    payload={"cliente": "[redacted]"},
                )
            ],
        )
    )
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

        assert response.status_code == 200
        assert response.json()["imported"] == 1
        assert response.json()["errors"][0]["row_number"] == 3
        import_mock.assert_called_once()
        assert import_mock.call_args.kwargs["commit"] is False
        db.commit.assert_called_once()
        assert audit_calls[0]["action"] == "import_checkins_csv"
        assert audit_calls[0]["details"]["totals"]["errors"] == 1
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
        assert response.json()["can_confirm"] is True
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
        details = audit_calls[0]["details"]
        assert details["file_type"] == ".csv"
        assert len(details["file_sha256"]) == 64
        assert details["mapping"] == {
            "mapped_fields": [],
            "mapped_columns": 0,
            "ignored_columns": 0,
        }
        assert details["totals"]["imported"] == 1
        assert "rows" not in details
        assert "payload" not in details
        db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_successful_import_audit_keeps_only_non_pii_mapping_metadata():
    details = imports_router._successful_import_audit_details(
        content=b"sensitive rows",
        filename="Alunos Matheus Setembro.csv",
        column_mappings={"cpf_do_aluno": "external_id", "data_acesso": "data_entrada"},
        ignored_columns=["observacao_professor"],
        summary=ImportSummary(imported=2, skipped_duplicates=0),
    )

    assert details["file_type"] == ".csv"
    assert "filename" not in details
    assert details["mapping"] == {
        "mapped_fields": ["data_entrada", "external_id"],
        "mapped_columns": 2,
        "ignored_columns": 1,
    }
    serialized = str(details)
    assert "Matheus" not in serialized
    assert "cpf_do_aluno" not in serialized
    assert "observacao_professor" not in serialized


def test_fully_invalid_checkin_commit_is_audited_before_blocking(app, client, mock_owner, monkeypatch):
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: mock_owner
    audit_calls: list[dict] = []

    monkeypatch.setattr("app.routers.imports.preview_checkins_csv", lambda *_args, **_kwargs: _unconfirmable_preview())
    monkeypatch.setattr(
        "app.routers.imports.log_audit_event",
        lambda *_args, **kwargs: audit_calls.append(kwargs),
    )

    try:
        response = client.post(
            "/api/v1/imports/checkins",
            files={"file": ("Acessos.csv", b"Cliente,Data Entrada\nEvelyn,data-invalida", "text/csv")},
        )

        assert response.status_code == 422
        assert audit_calls[0]["action"] == "import_checkins_csv_blocked"
        db.commit.assert_called_once()
    finally:
        app.dependency_overrides.clear()


def test_checkin_import_rolls_back_when_audit_cannot_be_recorded(app, client, mock_owner, monkeypatch):
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: mock_owner
    import_mock = MagicMock(return_value=ImportSummary(imported=1, skipped_duplicates=0))

    monkeypatch.setattr("app.routers.imports.preview_checkins_csv", lambda *_args, **_kwargs: _valid_preview())
    monkeypatch.setattr("app.routers.imports.import_checkins_csv", import_mock)
    monkeypatch.setattr(
        "app.routers.imports.log_audit_event",
        MagicMock(side_effect=RuntimeError("audit unavailable")),
    )

    try:
        response = client.post(
            "/api/v1/imports/checkins",
            files={"file": ("Acessos.csv", b"Cliente,Data Entrada\nEvelyn,27/08/2026", "text/csv")},
        )

        assert response.status_code == 500
        assert import_mock.call_args.kwargs["commit"] is False
        db.commit.assert_not_called()
    finally:
        app.dependency_overrides.clear()
