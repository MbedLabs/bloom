"""
* @file     ${tests/sec/BLOOM_exports.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The PDF exports render and are recorded, and an export holds only what its reader may see.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the export API with one project holding a customer and an internal requirement, each verified by a test case.
"""

from tests.sec.exports import ExportsBase


class ExportsTest(ExportsBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        password = values.API_PASSWORD
        bloom.bloom_start_full_api()
        self.project = bloom.bloom_create_export_project()
        bloom.bloom_add_admin(values.EXPORT_ADMIN_EMAIL, password)
        bloom.bloom_add_group_exporter(
            self.project, values.EXPORT_READER_EMAIL, values.EXPORT_READER_PERMISSIONS
        )
        bloom.bloom_add_group_exporter(
            self.project, values.EXPORT_AUTHOR_EMAIL, values.EXPORT_AUTHOR_PERMISSIONS
        )
        admin, _ = bloom.bloom_log_in(values.EXPORT_ADMIN_EMAIL, password)
        self.pdfs = [
            bloom.bloom_api_export(admin, self.project, kind, pdf=True)
            for kind in values.EXPORT_PDF_KINDS
        ]
        self.recorded = sorted(
            details["kind"]
            for details in bloom.bloom_list_audit_details(values.EXPORT_AUDIT_ACTION)
        )
        reader, _ = bloom.bloom_log_in(values.EXPORT_READER_EMAIL, password)
        requirements, matrix, tests = values.EXPORT_PDF_KINDS[:3]
        self.requirements = bloom.bloom_api_export(reader, self.project, requirements)
        self.matrix = bloom.bloom_api_export(reader, self.project, matrix)
        self.tests = bloom.bloom_api_export(reader, self.project, tests)
        self.author, _ = bloom.bloom_log_in(values.EXPORT_AUTHOR_EMAIL, password)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ExportsTest().run()
