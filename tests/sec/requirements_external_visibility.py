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
        listed = self.bloom.bloom_api_list_requirements(self.reader.headers, self.reader.project_id)
        self.print_variables({"status": listed.status, "body": listed.body})
        self.assertEqual(
            (listed.status, [item["req_id"] for item in listed.body["items"]]),
            (self.parameters.STATUS_OK, [self.parameters.READER_CUSTOMER_REQ]),
            msg=self.parameters.MSG_READER_REQ_LIST,
            abort_on_fail=False,
        )

    def bud_internal_requirement_is_hidden_404(self):
        hidden = self.bloom.bloom_api_read_requirement(self.reader.headers, self.internal)
        self.print_variables({"status": hidden.status, "body": hidden.body})
        self.assertEqual(
            hidden.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_READER_REQ_HIDDEN,
            abort_on_fail=False,
        )

    def bud_customer_origin_makes_a_requirement_customer_visible(self):
        created = self.bloom.bloom_api_create_requirement_of_origin(
            self.admin,
            self.reader.project_id,
            self.parameters.READER_NEW_TITLE,
            self.parameters.READER_CUSTOMER_ORIGIN,
        )
        self.print_variables({"status": created.status, "body": created.body})
        self.assertEqual(
            (
                created.status,
                created.body["req_origin"],
                created.body["visibility"],
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
        changed = self.bloom.bloom_api_set_requirement_origin(
            self.admin, self.customer, self.parameters.READER_INTERNAL_ORIGIN
        )
        self.print_variables({"status": changed.status, "body": changed.body})
        self.assertEqual(
            (
                changed.status,
                changed.body["req_origin"],
                changed.body["visibility"],
            ),
            (
                self.parameters.STATUS_OK,
                self.parameters.READER_INTERNAL_ORIGIN,
                self.parameters.INTERNAL_VISIBILITY,
            ),
            msg=self.parameters.MSG_READER_ORIGIN_INTERNAL,
            abort_on_fail=False,
        )
