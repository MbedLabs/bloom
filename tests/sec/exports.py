"""
* @file     ${tests/sec/exports.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests what the exports of a project hold and who gets them.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the project exports.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ExportsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_every_pdf_export_is_answered_as_a_pdf(self):
        for kind, export in zip(self.parameters.EXPORT_PDF_KINDS, self.pdfs):
            self.print_variables({"kind": kind, "status": export.status})
            self.assertEqual(
                (export.status, export.content_type, export.is_pdf),
                self.parameters.EXPORT_PDF,
                msg=self.parameters.MSG_EXPORT_PDF.format(kind=kind),
                abort_on_fail=False,
            )

    def bud_every_pdf_export_is_recorded(self):
        self.print_variables({"kinds": self.recorded})
        self.assertEqual(
            self.recorded,
            self.parameters.EXPORT_AUDIT_KINDS,
            msg=self.parameters.MSG_EXPORT_AUDITED,
            abort_on_fail=False,
        )

    def bud_external_exporter_gets_only_the_customer_requirement(self):
        self.print_variables({"rows": self.requirements.rows})
        self.assertEqual(
            (self.requirements.status, [row["req_id"] for row in self.requirements.rows]),
            (self.parameters.STATUS_OK, [self.parameters.EXPORT_SHOWN_REQ]),
            msg=self.parameters.MSG_EXPORT_REQUIREMENTS,
            abort_on_fail=False,
        )

    def bud_external_exporter_gets_only_the_customer_pair(self):
        self.print_variables({"rows": self.matrix.rows})
        self.assertEqual(
            [(row["req_id"], row["tc_id"]) for row in self.matrix.rows],
            [(self.parameters.EXPORT_SHOWN_REQ, self.parameters.EXPORT_SHOWN_TC)],
            msg=self.parameters.MSG_EXPORT_MATRIX,
            abort_on_fail=False,
        )

    def bud_external_exporter_gets_only_the_customer_test_case(self):
        self.print_variables({"rows": self.tests.rows})
        self.assertEqual(
            [row["tc_id"] for row in self.tests.rows],
            [self.parameters.EXPORT_SHOWN_TC],
            msg=self.parameters.MSG_EXPORT_TESTS,
            abort_on_fail=False,
        )

    def bud_exports_do_not_contain_the_internal_title(self):
        exports = (self.requirements, self.matrix, self.tests)
        for kind, export in zip(self.parameters.EXPORT_PDF_KINDS, exports):
            self.assertNotIn(
                self.parameters.EXPORT_HIDDEN_TITLE,
                export.text,
                msg=self.parameters.MSG_EXPORT_NO_HIDDEN.format(kind=kind),
                abort_on_fail=False,
            )

    def bud_dossier_is_refused_without_test_case_export_403(self):
        dossier = self.bloom.bloom_api_export(
            self.author, self.project, self.parameters.EXPORT_DOSSIER
        )
        self.print_variables({"status": dossier.status})
        self.assertEqual(
            dossier.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_EXPORT_DOSSIER,
            abort_on_fail=False,
        )
