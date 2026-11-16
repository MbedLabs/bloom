"""
* @file     ${tests/sec/artefacts_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which requirements' related artefacts an external reader gets.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the related artefacts an external reader reads.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ArtefactsExternalVisibilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_related_of_an_internal_requirement_is_hidden_404(self):
        self.print_variables({"status": self.hidden.status, "body": self.hidden.body})
        self.assertEqual(
            self.hidden.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_READER_RELATED_HIDDEN,
            abort_on_fail=False,
        )

    def bud_related_of_a_customer_requirement_is_shown_200(self):
        self.print_variables({"status": self.visible.status, "body": self.visible.body})
        self.assertEqual(
            self.visible.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_READER_RELATED_SHOWN,
            abort_on_fail=False,
        )
