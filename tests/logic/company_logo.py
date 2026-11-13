"""
* @file     ${tests/logic/company_logo.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests storing the company logo and placing it in PDF reports.
* @author   Amine El Omari
* @date     2026-11-13
* @version  1.0.0
* @note     Base class containing the bud methods of the company logo.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class CompanyLogoBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_logo_is_stored_served_and_deleted(self):
        png = self.parameters.LOGO_PNG
        self.print_variables(
            {
                "stored": vars(self.tc_stored),
                "served": (self.tc_served.status, self.tc_served.media_type),
                "after delete": self.tc_deleted.status,
            }
        )
        self._equal(
            self.tc_stored.content_type,
            self.parameters.LOGO_PNG_TYPE,
            self.parameters.MSG_LOGO_TYPE,
        )
        self._equal(self.tc_stored.size, len(png), self.parameters.MSG_LOGO_SIZE)
        self._equal(self.tc_served.body, png, self.parameters.MSG_LOGO_BODY)
        self._equal(
            self.tc_served.media_type, self.parameters.LOGO_PNG_TYPE, self.parameters.MSG_LOGO_MEDIA
        )
        self._equal(self.tc_report_logo, png, self.parameters.MSG_LOGO_REPORT)
        self._equal(
            self.tc_deleted.status,
            self.parameters.STATUS_NOT_FOUND,
            self.parameters.MSG_LOGO_DELETED,
        )
        self._equal(self.tc_report_after, None, self.parameters.MSG_LOGO_REPORT_NONE)

    def bud_non_image_is_refused(self):
        self.print_variables(vars(self.tc_text))
        self._equal(
            self.tc_text.status,
            self.parameters.STATUS_UNSUPPORTED_MEDIA,
            self.parameters.MSG_LOGO_NOT_IMAGE,
        )

    def bud_requirements_pdf_embeds_the_logo(self):
        header = self.parameters.LOGO_PDF_HEADER
        self.print_variables(
            {
                "without": (self.tc_pdf_plain[:8], len(self.tc_pdf_plain)),
                "with": (self.tc_pdf_logo[:8], len(self.tc_pdf_logo)),
            }
        )
        self._equal(self.tc_pdf_plain[: len(header)], header, self.parameters.MSG_LOGO_PDF)
        self._equal(self.tc_pdf_logo[: len(header)], header, self.parameters.MSG_LOGO_PDF)
        self.assertTrue(
            len(self.tc_pdf_logo) >= len(self.tc_pdf_plain),
            msg=self.parameters.MSG_LOGO_PDF_SIZE,
            expected=f">= {len(self.tc_pdf_plain)}",
            actual=len(self.tc_pdf_logo),
            abort_on_fail=False,
        )

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
