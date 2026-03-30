from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.routers.reports import dispatch_monthly_reports


def test_dispatch_monthly_reports_is_blocked_when_disabled():
    with patch("app.routers.reports.settings.monthly_reports_dispatch_enabled", False):
        with pytest.raises(HTTPException) as exc_info:
            dispatch_monthly_reports(
                request=MagicMock(),
                db=MagicMock(),
                current_user=SimpleNamespace(),
            )

    assert exc_info.value.status_code == 503
