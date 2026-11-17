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
        stored = self.bloom.bloom_set_logo(png, self.parameters.LOGO_PNG_TYPE)
        served = self.bloom.bloom_get_logo()
        report_logo = self.bloom.bloom_report_logo()
        self.bloom.bloom_delete_logo()
        deleted = self.bloom.bloom_get_logo()
        report_after = self.bloom.bloom_report_logo()
        self.print_variables(
            {
                "stored": vars(stored),
                "served": (served.status, served.media_type),
                "after delete": deleted.status,
            }
        )
        self._equal(
            stored.content_type,
            self.parameters.LOGO_PNG_TYPE,
            self.parameters.MSG_LOGO_TYPE,
        )
        self._equal(stored.size, len(png), self.parameters.MSG_LOGO_SIZE)
        self._equal(served.body, png, self.parameters.MSG_LOGO_BODY)
        self._equal(
            served.media_type, self.parameters.LOGO_PNG_TYPE, self.parameters.MSG_LOGO_MEDIA
        )
        self._equal(report_logo, png, self.parameters.MSG_LOGO_REPORT)
        self._equal(
            deleted.status,
            self.parameters.STATUS_NOT_FOUND,
            self.parameters.MSG_LOGO_DELETED,
        )
        self._equal(report_after, None, self.parameters.MSG_LOGO_REPORT_NONE)

    def bud_non_image_is_refused(self):
        text = self.bloom.bloom_set_logo(
            self.parameters.LOGO_NOT_IMAGE, self.parameters.LOGO_TEXT_TYPE
        )
        self.print_variables(vars(text))
        self._equal(
            text.status,
            self.parameters.STATUS_UNSUPPORTED_MEDIA,
            self.parameters.MSG_LOGO_NOT_IMAGE,
        )

    def bud_requirements_pdf_embeds_the_logo(self):
        pdf_plain = self.bloom.bloom_requirements_pdf(None)
        pdf_logo = self.bloom.bloom_requirements_pdf(self.parameters.LOGO_PNG)
        header = self.parameters.LOGO_PDF_HEADER
        self.print_variables(
            {
                "without": (pdf_plain[:8], len(pdf_plain)),
                "with": (pdf_logo[:8], len(pdf_logo)),
            }
        )
        self._equal(pdf_plain[: len(header)], header, self.parameters.MSG_LOGO_PDF)
        self._equal(pdf_logo[: len(header)], header, self.parameters.MSG_LOGO_PDF)
        self.assertTrue(
            len(pdf_logo) >= len(pdf_plain),
            msg=self.parameters.MSG_LOGO_PDF_SIZE,
            expected=f">= {len(pdf_plain)}",
            actual=len(pdf_logo),
            abort_on_fail=False,
        )

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
