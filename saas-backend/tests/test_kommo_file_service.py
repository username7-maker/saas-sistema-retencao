import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.models import KommoFileAttachment
from app.services.kommo_file_service import upload_and_attach_pdf_to_lead
from app.services.kommo_service import KommoServiceError


GYM_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
MEMBER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def _gym():
    return SimpleNamespace(
        id=GYM_ID,
        kommo_base_url="https://example.kommo.com",
        kommo_access_token_encrypted="token",
    )


def _member():
    return SimpleNamespace(id=MEMBER_ID, full_name="Aluno Teste")


def test_upload_and_attach_pdf_to_lead_uploads_and_attaches_file():
    db = MagicMock()
    db.scalar.return_value = None

    with (
        patch("app.services.kommo_file_service.get_kommo_drive_url", return_value="https://drive.kommo.com") as get_drive,
        patch("app.services.kommo_file_service.create_upload_session", return_value={"session_token": "session-1"}) as create_session,
        patch("app.services.kommo_file_service.upload_file_bytes", return_value="file-uuid-1") as upload_bytes,
        patch("app.services.kommo_file_service.attach_file_to_lead") as attach_file,
    ):
        result = upload_and_attach_pdf_to_lead(
            db,
            gym=_gym(),
            member=_member(),
            domain="body_composition",
            source_type="body_composition",
            source_id="eval-1",
            lead_id="12345",
            contact_id="67890",
            file_bytes=b"%PDF-1.4 test",
            file_name="relatorio.pdf",
        )

    assert result.file_uuid == "file-uuid-1"
    assert result.upload_status == "uploaded"
    assert result.attach_status == "attached"
    assert result.attachment.kommo_lead_id == "12345"
    assert result.attachment.file_name == "relatorio.pdf"
    get_drive.assert_called_once()
    create_session.assert_called_once()
    upload_bytes.assert_called_once()
    attach_file.assert_called_once()
    assert db.flush.call_count >= 2


def test_upload_and_attach_pdf_to_lead_reuses_valid_existing_attachment():
    db = MagicMock()
    existing = KommoFileAttachment(
        gym_id=GYM_ID,
        member_id=MEMBER_ID,
        domain="body_composition",
        source_type="body_composition",
        source_id="eval-1",
        kommo_lead_id="12345",
        file_uuid="existing-file",
        file_name="relatorio.pdf",
        upload_status="uploaded",
        attach_status="attached",
    )
    db.scalar.return_value = existing

    with patch("app.services.kommo_file_service.get_kommo_drive_url") as get_drive:
        result = upload_and_attach_pdf_to_lead(
            db,
            gym=_gym(),
            member=_member(),
            domain="body_composition",
            source_type="body_composition",
            source_id="eval-1",
            lead_id="12345",
            contact_id="67890",
            file_bytes=b"%PDF-1.4 test",
            file_name="novo.pdf",
        )

    assert result.file_uuid == "existing-file"
    assert result.file_name == "relatorio.pdf"
    get_drive.assert_not_called()
    db.add.assert_not_called()


def test_upload_and_attach_pdf_to_lead_marks_attachment_failed_when_kommo_fails():
    db = MagicMock()
    db.scalar.return_value = None

    with patch("app.services.kommo_file_service.get_kommo_drive_url", side_effect=KommoServiceError("kommo_files_scope_missing")):
        with pytest.raises(KommoServiceError):
            upload_and_attach_pdf_to_lead(
                db,
                gym=_gym(),
                member=_member(),
                domain="body_composition",
                source_type="body_composition",
                source_id="eval-1",
                lead_id="12345",
                contact_id="67890",
                file_bytes=b"%PDF-1.4 test",
                file_name="relatorio.pdf",
            )

    added_attachments = [call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], KommoFileAttachment)]
    assert added_attachments
    attachment = added_attachments[-1]
    assert attachment.upload_status == "failed"
    assert attachment.attach_status == "failed"
    assert "kommo_files_scope_missing" in (attachment.error_detail or "")
