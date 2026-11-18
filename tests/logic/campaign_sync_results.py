"""
* @file     ${tests/logic/campaign_sync_results.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests how synced automated results reach a test case.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the campaign result sync.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class CampaignSyncResultsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_latest_result_is_applied(self):
        latest = self.bloom.bloom_apply_test_result(
            self.parameters.SYNC_RESULT_EMPTY_CASE, self.parameters.SYNC_RESULT_FAILED
        )
        case = latest.case
        result = self.parameters.SYNC_RESULT_FAILED
        self.print_variables({"applied": latest.applied, "case": vars(case)})
        self.assertTrue(
            latest.applied is True,
            msg=self.parameters.MSG_SYNC_RESULT_APPLIED,
            expected=True,
            actual=latest.applied,
            abort_on_fail=False,
        )
        checks = (
            (case.last_execution_status, result["status"], self.parameters.MSG_SYNC_RESULT_STATUS),
            (
                case.last_execution_comment,
                result["comment"],
                self.parameters.MSG_SYNC_RESULT_COMMENT,
            ),
            (case.last_bud_run_id, result["bud_run_id"], self.parameters.MSG_SYNC_RESULT_RUN),
        )
        for actual, expected, message in checks:
            self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
        self.assertTrue(
            case.last_executed_at is not None,
            msg=self.parameters.MSG_SYNC_RESULT_TIME,
            expected="a time",
            actual=case.last_executed_at,
            abort_on_fail=False,
        )

    def bud_older_result_is_ignored(self):
        older = self.bloom.bloom_apply_test_result(
            self.parameters.SYNC_RESULT_NEWER_CASE, self.parameters.SYNC_RESULT_OLDER
        )
        case = older.case
        kept = self.parameters.SYNC_RESULT_NEWER_CASE
        self.print_variables({"applied": older.applied, "case": vars(case)})
        self.assertTrue(
            older.applied is False,
            msg=self.parameters.MSG_SYNC_RESULT_OLDER,
            expected=False,
            actual=older.applied,
            abort_on_fail=False,
        )
        for field in ("last_execution_status", "last_execution_comment", "last_bud_run_id"):
            self.assertEqual(
                getattr(case, field),
                kept[field],
                msg=f"{self.parameters.MSG_SYNC_RESULT_KEPT}: {field}",
                abort_on_fail=False,
            )

    def bud_sync_payload_is_bounded(self):
        too_many = self.bloom.bloom_build_sync_request(
            self.parameters.SYNC_RESULT_TC_ID,
            self.parameters.SYNC_RESULT_STATUS,
            self.parameters.SYNC_RESULT_TOO_MANY,
        )
        self.print_variables({"results": self.parameters.SYNC_RESULT_TOO_MANY, "refusal": too_many})
        self.assertEqual(
            too_many,
            self.parameters.SYNC_RESULT_REFUSAL,
            msg=self.parameters.MSG_SYNC_RESULT_BOUNDED,
            abort_on_fail=False,
        )
