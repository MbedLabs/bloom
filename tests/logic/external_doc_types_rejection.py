"""
* @file     ${tests/logic/external_doc_types_rejection.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that an external member is refused an ungranted document type.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the refused document type.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ExternalDocTypesRejectionBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_other_type_is_refused(self):
        self.print_variables(
            {
                "granted": self.parameters.EXTERNAL_GRANTED,
                "type": self.parameters.EXTERNAL_OTHER_TYPE,
                "refusal": self.tc_access.status,
                "detail": self.tc_access.detail,
            }
        )
        self.assertRegex(
            self.tc_access.detail,
            self.parameters.EXTERNAL_REFUSAL_PATTERN,
            msg=self.parameters.MSG_EXTERNAL_OTHER_REFUSED,
            abort_on_fail=False,
        )
