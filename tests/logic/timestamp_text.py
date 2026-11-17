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
        naive = self.bloom.bloom_minute_utc(self.parameters.STAMP_NAIVE)
        self.print_variables({"time": self.parameters.STAMP_NAIVE, "text": naive})
        self.assertEqual(
            naive,
            self.parameters.STAMP_TEXT,
            msg=self.parameters.MSG_STAMP_MINUTES,
            abort_on_fail=False,
        )

    def bud_missing_time_is_empty(self):
        none = self.bloom.bloom_minute_utc(None)
        self.print_variables({"text": none})
        self.assertEqual(
            none,
            self.parameters.STAMP_NONE_TEXT,
            msg=self.parameters.MSG_STAMP_NONE,
            abort_on_fail=False,
        )

    def bud_aware_time_is_written_in_utc(self):
        aware = self.bloom.bloom_minute_utc(self.parameters.STAMP_AWARE)
        self.print_variables({"time": self.parameters.STAMP_AWARE, "text": aware})
        self.assertEqual(
            aware,
            self.parameters.STAMP_TEXT,
            msg=self.parameters.MSG_STAMP_AWARE,
            abort_on_fail=False,
        )

    def bud_execution_time_is_stored_in_utc(self):
        stored = self.bloom.bloom_resolve_execution_time_in_zone(
            self.parameters.STAMP_EXECUTED, self.parameters.STAMP_SERVER_ZONE
        )
        self.print_variables(
            {
                "zone": self.parameters.STAMP_SERVER_ZONE,
                "executed": self.parameters.STAMP_EXECUTED,
                "stored": stored,
            }
        )
        self.assertEqual(
            stored,
            self.parameters.STAMP_EXECUTED_STORED,
            msg=self.parameters.MSG_STAMP_EXECUTION_UTC,
            abort_on_fail=False,
        )
