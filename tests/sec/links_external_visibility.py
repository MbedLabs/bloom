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
        listed = self.bloom.bloom_api_list_links(self.reader.headers, self.reader.project_id)
        self.print_variables({"status": listed.status, "body": listed.body})
        self.assertEqual(
            (
                listed.status,
                [(item["source_id"], item["target_id"]) for item in listed.body],
            ),
            (self.parameters.STATUS_OK, [self.customer_ends]),
            msg=self.parameters.MSG_READER_LINKS,
            abort_on_fail=False,
        )
