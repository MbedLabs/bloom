"""
* @file     ${tests/logic/timestamp_text.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the times Bloom writes for people and stores for executions.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the time text.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class TimestampTextBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_time_stops_at_minutes(self):
        self.print_variables({"time": self.parameters.STAMP_NAIVE, "text": self.naive})
        self.assertEqual(
            self.naive,
            self.parameters.STAMP_TEXT,
            msg=self.parameters.MSG_STAMP_MINUTES,
            abort_on_fail=False,
        )

    def bud_missing_time_is_empty(self):
        self.print_variables({"text": self.none})
        self.assertEqual(
            self.none,
            self.parameters.STAMP_NONE_TEXT,
            msg=self.parameters.MSG_STAMP_NONE,
            abort_on_fail=False,
        )

    def bud_aware_time_is_written_in_utc(self):
        self.print_variables({"time": self.parameters.STAMP_AWARE, "text": self.aware})
        self.assertEqual(
            self.aware,
            self.parameters.STAMP_TEXT,
            msg=self.parameters.MSG_STAMP_AWARE,
            abort_on_fail=False,
        )

    def bud_execution_time_is_stored_in_utc(self):
        self.print_variables(
            {
                "zone": self.parameters.STAMP_SERVER_ZONE,
                "executed": self.parameters.STAMP_EXECUTED,
                "stored": self.stored,
            }
        )
        self.assertEqual(
            self.stored,
            self.parameters.STAMP_EXECUTED_STORED,
            msg=self.parameters.MSG_STAMP_EXECUTION_UTC,
            abort_on_fail=False,
        )
