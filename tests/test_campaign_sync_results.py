from types import SimpleNamespace

from app.api.campaigns import _apply_result_to_test_case


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

    _apply_result_to_test_case(tc, result)

    assert tc.last_execution_status == "Failed"
    assert tc.last_execution_comment == "Route endpoint returned fabricated polyline."
    assert tc.last_bud_run_id == 5
    assert tc.last_executed_at is not None
