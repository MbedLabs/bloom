from datetime import datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.api.campaigns import _apply_result_to_test_case
from app.schemas import AutomatedResult, SyncResultsRequest


def test_apply_result_to_test_case_persists_latest_execution_summary():
    tc = SimpleNamespace(
        last_execution_status=None,
        last_executed_at=None,
        last_execution_comment=None,
        last_bud_run_id=None,
    )
    result = SimpleNamespace(
        status="Failed",
        executed_at=None,
        comment="Route endpoint returned fabricated polyline.",
        bud_run_id=5,
    )

    assert _apply_result_to_test_case(tc, result) is True

    assert tc.last_execution_status == "Failed"
    assert tc.last_execution_comment == "Route endpoint returned fabricated polyline."
    assert tc.last_bud_run_id == 5
    assert tc.last_executed_at is not None


def test_older_result_is_not_applied_to_test_case():
    tc = SimpleNamespace(
        last_execution_status="Passed",
        last_executed_at=datetime(2026, 7, 22, 12, 0, 0),
        last_execution_comment="newer",
        last_bud_run_id=8,
    )
    result = SimpleNamespace(
        status="Failed",
        executed_at=datetime(2026, 7, 22, 11, 0, 0),
        comment="older",
        bud_run_id=7,
    )

    assert _apply_result_to_test_case(tc, result) is False
    assert tc.last_execution_status == "Passed"
    assert tc.last_execution_comment == "newer"
    assert tc.last_bud_run_id == 8


def test_sync_payload_has_a_bounded_result_count():
    item = AutomatedResult(tc_id="PRJ-TC-001", status="Passed")

    with pytest.raises(ValidationError):
        SyncResultsRequest(results=[item] * 1001)
