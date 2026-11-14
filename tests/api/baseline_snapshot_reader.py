"""
* @file     ${tests/api/baseline_snapshot_reader.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests what a reader with limited access gets from a stored baseline.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     Base class containing the bud methods of the baseline snapshot reader.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class BaselineSnapshotReaderBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_setup_calls_succeed(self):
        self.print_variables({"setup": self.tc_setup})
        self.assertEqual(
            [found for found, _ in self.tc_setup],
            [expected for _, expected in self.tc_setup],
            msg=self.parameters.MSG_API_SETUP,
            abort_on_fail=True,
        )

    def bud_reader_opens_the_baseline(self):
        self.print_variables({"status": self.tc_detail.status_code})
        self.assertEqual(
            self.tc_detail.status_code,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_SNAPSHOT_OPENS,
            abort_on_fail=True,
        )

    def bud_requirement_record_is_shown(self):
        records = self.tc_detail.json()["snapshot"]["requirements"]["records"]
        self.print_variables({"requirement records": [record["id"] for record in records]})
        self.assertEqual(
            [record["id"] for record in records],
            [self.tc_requirement["id"]],
            msg=self.parameters.MSG_SNAPSHOT_REQUIREMENT,
            abort_on_fail=False,
        )

    def bud_no_document_record_is_shown(self):
        records = self.tc_detail.json()["snapshot"]["documents"]["records"]
        self.print_variables({"document records": records})
        self.assertEqual(
            records, [], msg=self.parameters.MSG_SNAPSHOT_NO_DOCUMENT, abort_on_fail=False
        )

    def bud_captured_document_count_is_kept(self):
        count = self.tc_detail.json()["snapshot"]["documents"]["count"]
        self.print_variables({"document count": count})
        self.assertEqual(
            count,
            self.parameters.SNAPSHOT_CAPTURED_DOCUMENTS,
            msg=self.parameters.MSG_SNAPSHOT_COUNT,
            abort_on_fail=False,
        )

    def bud_document_title_is_hidden(self):
        titles = self.tc_detail.json()["snapshot"]["documents"]["titles"]
        self.print_variables({"document titles": titles})
        self.assertNotIn(
            self.parameters.SNAPSHOT_DOCUMENT_TITLE,
            titles,
            msg=self.parameters.MSG_SNAPSHOT_TITLE_HIDDEN,
            abort_on_fail=False,
        )

    def bud_list_carries_ids_without_records(self):
        listed = [item for item in self.tc_listed.json() if item["id"] == self.tc_baseline_id]
        requirements = listed[0]["snapshot"]["requirements"] if listed else {}
        found = (
            self.tc_listed.status_code,
            len(listed),
            "records" in requirements,
            requirements.get("ids"),
        )
        self.print_variables({"status, listed, records, ids": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_OK, 1, False, [self.tc_requirement["req_id"]]),
            msg=self.parameters.MSG_SNAPSHOT_LIST,
            abort_on_fail=False,
        )
