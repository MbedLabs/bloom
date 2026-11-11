"""
* @file     ${tests/logic/project_variables.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests updating a project variable and refusing a duplicate key.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the project variables.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ProjectVariablesBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_update_writes_kind_key_value_and_description(self):
        outcome = self.tc_updated
        self.print_variables(
            {"item": outcome.item, "flushes": outcome.flushes, "refreshes": outcome.refreshed_item}
        )
        self.assertTrue(
            outcome.same_item,
            msg=self.parameters.MSG_VARIABLE_SAME_ITEM,
            expected=True,
            actual=outcome.same_item,
            abort_on_fail=False,
        )
        for field, value in self.parameters.VARIABLE_UPDATE.items():
            self.assertEqual(
                outcome.item[field],
                value,
                msg=f"{self.parameters.MSG_VARIABLE_FIELD}: {field}",
                abort_on_fail=False,
            )
        self.assertEqual(
            outcome.flushes,
            self.parameters.VARIABLE_ONE_WRITE,
            msg=self.parameters.MSG_VARIABLE_FLUSHED,
            abort_on_fail=False,
        )
        self.assertEqual(
            outcome.refreshed_item,
            [True],
            msg=self.parameters.MSG_VARIABLE_REFRESHED,
            abort_on_fail=False,
        )

    def bud_duplicate_kind_and_key_is_refused(self):
        outcome = self.tc_duplicate
        self.print_variables(
            {"status": outcome.status, "detail": outcome.detail, "flushes": outcome.flushes}
        )
        self.assertEqual(
            outcome.status,
            self.parameters.STATUS_BAD_REQUEST,
            msg=self.parameters.MSG_VARIABLE_DUPLICATE,
            abort_on_fail=False,
        )
        self.assertEqual(
            outcome.detail,
            self.parameters.VARIABLE_DUPLICATE_DETAIL,
            msg=self.parameters.MSG_VARIABLE_DUPLICATE_DETAIL,
            abort_on_fail=False,
        )
        self.assertEqual(
            outcome.flushes,
            self.parameters.VARIABLE_NO_WRITE,
            msg=self.parameters.MSG_VARIABLE_NOT_WRITTEN,
            abort_on_fail=False,
        )
        self.assertEqual(
            outcome.refreshed_item,
            [],
            msg=self.parameters.MSG_VARIABLE_NOT_WRITTEN,
            abort_on_fail=False,
        )
