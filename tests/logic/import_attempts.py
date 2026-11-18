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
        first = self.bloom.bloom_begin_import(self.busy_user, self.busy_project)
        second = self.bloom.bloom_begin_import(self.busy_user, self.busy_project)
        self.bloom.bloom_finish_import(first.id, self.parameters.IMPORT_COMPLETED)
        self.print_variables({"first": vars(first), "second": vars(second)})
        self.assertTrue(
            first.id is not None,
            msg=self.parameters.MSG_IMPORT_FIRST,
            expected="an attempt id",
            actual=first.status,
            abort_on_fail=False,
        )
        self.assertEqual(
            second.status,
            self.parameters.STATUS_TOO_MANY,
            msg=self.parameters.MSG_IMPORT_ACTIVE,
            abort_on_fail=False,
        )

    def bud_import_starts_are_limited_per_user(self):
        self.bloom.bloom_limit_imports(self.parameters.IMPORT_STARTS_ALLOWED)
        allowed = []
        for _ in range(self.parameters.IMPORT_STARTS_ALLOWED):
            start = self.bloom.bloom_begin_import(self.limited_user, self.limited_project)
            allowed.append(start)
            self.bloom.bloom_finish_import(start.id, self.parameters.IMPORT_COMPLETED)
        limited = self.bloom.bloom_begin_import(self.limited_user, self.limited_project)
        recorded = self.bloom.bloom_count_imports(self.limited_user)
        self.print_variables(
            {
                "allowed": [vars(start) for start in allowed],
                "past the limit": vars(limited),
                "recorded": recorded,
            }
        )
        for start in allowed:
            self.assertEqual(
                start.status, None, msg=self.parameters.MSG_IMPORT_STARTS, abort_on_fail=False
            )
        self.assertEqual(
            limited.status,
            self.parameters.STATUS_TOO_MANY,
            msg=self.parameters.MSG_IMPORT_LIMITED,
            abort_on_fail=False,
        )
        self.assertEqual(
            limited.retry_after,
            self.parameters.IMPORT_RETRY_SECONDS,
            msg=self.parameters.MSG_IMPORT_RETRY,
            abort_on_fail=False,
        )
        self.assertEqual(
            recorded,
            self.parameters.IMPORT_STARTS_ALLOWED,
            msg=self.parameters.MSG_IMPORT_COUNT,
            abort_on_fail=False,
        )
