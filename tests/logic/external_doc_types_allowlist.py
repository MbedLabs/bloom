"""
* @file     ${tests/logic/external_doc_types_allowlist.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the document types an external member's term grants.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the external allowlist.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ExternalDocTypesAllowlistBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_allowlist_is_the_granted_types(self):
        self.print_variables(
            {"granted": self.parameters.EXTERNAL_ALLOWLIST, "allowed": self.tc_allowed}
        )
        self.assertEqual(
            self.tc_allowed,
            self.parameters.EXTERNAL_ALLOWLIST_EXPECTED,
            msg=self.parameters.MSG_EXTERNAL_ALLOWLIST,
            abort_on_fail=False,
        )
