"""
* @file     ${tests/sec/links_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which links an external reader lists.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the links an external reader lists.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class LinksExternalVisibilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_external_reader_lists_only_the_link_between_customer_artefacts(self):
        self.print_variables({"status": self.tc_listed.status, "body": self.tc_listed.body})
        self.assertEqual(
            (
                self.tc_listed.status,
                [(item["source_id"], item["target_id"]) for item in self.tc_listed.body],
            ),
            (self.parameters.STATUS_OK, [self.tc_customer_ends]),
            msg=self.parameters.MSG_READER_LINKS,
            abort_on_fail=False,
        )
