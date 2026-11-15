"""
* @file     ${tests/logic/external_doc_types_admin.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the document types an admin may see in a project.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the admin's document types.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ExternalDocTypesAdminBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_admin_sees_every_type(self):
        self.print_variables({"allowed": self.tc_admin.allowed})
        self.assertEqual(
            self.tc_admin.allowed,
            self.parameters.EXTERNAL_EVERY_TYPE,
            msg=self.parameters.MSG_EXTERNAL_ADMIN_EVERY_TYPE,
            abort_on_fail=False,
        )

    def bud_admin_needs_no_query(self):
        self.print_variables({"queries": self.tc_admin.queries})
        self.assertEqual(
            self.tc_admin.queries,
            self.parameters.EXTERNAL_NO_QUERY,
            msg=self.parameters.MSG_EXTERNAL_ADMIN_NO_QUERY,
            abort_on_fail=False,
        )
