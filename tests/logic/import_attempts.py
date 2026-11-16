"""
* @file     ${tests/logic/import_attempts.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the ReqIF import concurrency and rate controls.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the import attempts.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ImportAttemptsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_one_active_import_per_project(self):
        self.print_variables({"first": vars(self.first), "second": vars(self.second)})
        self.assertTrue(
            self.first.id is not None,
            msg=self.parameters.MSG_IMPORT_FIRST,
            expected="an attempt id",
            actual=self.first.status,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.second.status,
            self.parameters.STATUS_TOO_MANY,
            msg=self.parameters.MSG_IMPORT_ACTIVE,
            abort_on_fail=False,
        )

    def bud_import_starts_are_limited_per_user(self):
        self.print_variables(
            {
                "allowed": [vars(start) for start in self.allowed],
                "past the limit": vars(self.limited),
                "recorded": self.recorded,
            }
        )
        for start in self.allowed:
            self.assertEqual(
                start.status, None, msg=self.parameters.MSG_IMPORT_STARTS, abort_on_fail=False
            )
        self.assertEqual(
            self.limited.status,
            self.parameters.STATUS_TOO_MANY,
            msg=self.parameters.MSG_IMPORT_LIMITED,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.limited.retry_after,
            self.parameters.IMPORT_RETRY_SECONDS,
            msg=self.parameters.MSG_IMPORT_RETRY,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.recorded,
            self.parameters.IMPORT_STARTS_ALLOWED,
            msg=self.parameters.MSG_IMPORT_COUNT,
            abort_on_fail=False,
        )
