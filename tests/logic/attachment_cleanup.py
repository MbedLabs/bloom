"""
* @file     ${tests/logic/attachment_cleanup.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the reconciliation of the attachment volume with the stored attachments.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the attachment cleanup.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class AttachmentCleanupBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_reconciliation_removes_only_old_unreferenced_files(self):
        values = self.parameters
        result = self.bloom.bloom_reconcile_attachments(
            [values.ACL_REFERENCED, values.ACL_FRESH, values.ACL_OLD],
            [values.ACL_REFERENCED, values.ACL_MISSING],
            values.ACL_OLD,
            values.ACL_GRACE_SECONDS,
            values.ACL_OLD_AGE_SECONDS,
        )
        self.print_variables(
            {
                "orphans": result.report.orphan_files,
                "missing": result.report.missing_files,
                "kept": result.kept,
            }
        )
        self.assertEqual(
            (result.report.orphan_files, result.report.missing_files),
            (1, 1),
            msg=values.MSG_ACL_COUNTS,
            abort_on_fail=False,
        )
        self.assertEqual(
            result.kept,
            sorted([values.ACL_FRESH, values.ACL_REFERENCED]),
            msg=values.MSG_ACL_FILES,
            abort_on_fail=False,
        )
        self.assertTrue(result.committed, msg=values.MSG_ACL_COMMITTED, abort_on_fail=False)

    def bud_the_application_start_runs_the_reconciliation(self):
        same_session, calls = self.bloom.bloom_lifespan_reconcile_calls()
        self.print_variables({"calls": calls})
        self.assertEqual(
            (same_session, calls),
            (True, 1),
            msg=self.parameters.MSG_ACL_LIFESPAN,
            abort_on_fail=False,
        )
