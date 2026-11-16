"""
* @file     ${tests/sec/requirements_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which requirements an external reader gets and how the origin sets the visibility.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the requirements an external reader reads.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class RequirementsExternalVisibilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_external_reader_lists_only_the_customer_requirement(self):
        self.print_variables({"status": self.listed.status, "body": self.listed.body})
        self.assertEqual(
            (self.listed.status, [item["req_id"] for item in self.listed.body["items"]]),
            (self.parameters.STATUS_OK, [self.parameters.READER_CUSTOMER_REQ]),
            msg=self.parameters.MSG_READER_REQ_LIST,
            abort_on_fail=False,
        )

    def bud_internal_requirement_is_hidden_404(self):
        self.print_variables({"status": self.hidden.status, "body": self.hidden.body})
        self.assertEqual(
            self.hidden.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_READER_REQ_HIDDEN,
            abort_on_fail=False,
        )

    def bud_customer_origin_makes_a_requirement_customer_visible(self):
        self.print_variables({"status": self.created.status, "body": self.created.body})
        self.assertEqual(
            (
                self.created.status,
                self.created.body["req_origin"],
                self.created.body["visibility"],
            ),
            (
                self.parameters.STATUS_CREATED,
                self.parameters.READER_CUSTOMER_ORIGIN,
                self.parameters.CUSTOMER_VISIBILITY,
            ),
            msg=self.parameters.MSG_READER_ORIGIN_CUSTOMER,
            abort_on_fail=False,
        )

    def bud_internal_origin_makes_a_requirement_internal(self):
        self.print_variables({"status": self.changed.status, "body": self.changed.body})
        self.assertEqual(
            (
                self.changed.status,
                self.changed.body["req_origin"],
                self.changed.body["visibility"],
            ),
            (
                self.parameters.STATUS_OK,
                self.parameters.READER_INTERNAL_ORIGIN,
                self.parameters.INTERNAL_VISIBILITY,
            ),
            msg=self.parameters.MSG_READER_ORIGIN_INTERNAL,
            abort_on_fail=False,
        )
