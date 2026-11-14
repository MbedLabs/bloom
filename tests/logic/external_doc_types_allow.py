"""
* @file     ${tests/logic/external_doc_types_allow.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that an external member may open a granted document type.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the granted document type.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ExternalDocTypesAllowBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_granted_type_is_allowed(self):
        self.print_variables(
            {
                "granted": self.parameters.EXTERNAL_GRANTED,
                "type": self.parameters.EXTERNAL_GRANTED_TYPE,
                "refusal": self.tc_access.status,
                "detail": self.tc_access.detail,
            }
        )
        self.assertEqual(
            self.tc_access.status,
            self.parameters.EXTERNAL_NOT_REFUSED,
            msg=self.parameters.MSG_EXTERNAL_GRANTED_ALLOWED,
            abort_on_fail=False,
        )
