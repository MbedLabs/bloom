"""
* @file     ${tests/logic/BLOOM_company_logo.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An admin stores, reads and deletes the company logo; PDF reports carry it.
* @author   Amine El Omari
* @date     2026-11-13
* @version  1.0.0
* @note     This module tests the logo handlers and the requirements report directly.
"""

from tests.logic.company_logo import CompanyLogoBase


class CompanyLogoTest(CompanyLogoBase):

    def setUpClass(self):
        super().setUpClass()
        bloom = self.bloom
        project_id = bloom.bloom_create_project(self.parameters.LOGO_PREFIX)
        bloom.bloom_add_user(
            self.parameters.LOGO_ADMIN, bloom.bloom_role(self.parameters.LOGO_ADMIN_ROLE)
        )
        bloom.bloom_add_artefact(
            self.parameters.LOGO_REQUIREMENT_KIND,
            project_id=project_id,
            **self.parameters.LOGO_REQUIREMENT,
        )
        png = self.parameters.LOGO_PNG
        self.tc_stored = bloom.bloom_set_logo(png, self.parameters.LOGO_PNG_TYPE)
        self.tc_served = bloom.bloom_get_logo()
        self.tc_report_logo = bloom.bloom_report_logo()
        bloom.bloom_delete_logo()
        self.tc_deleted = bloom.bloom_get_logo()
        self.tc_report_after = bloom.bloom_report_logo()
        self.tc_text = bloom.bloom_set_logo(
            self.parameters.LOGO_NOT_IMAGE, self.parameters.LOGO_TEXT_TYPE
        )
        self.tc_pdf_plain = bloom.bloom_requirements_pdf(None)
        self.tc_pdf_logo = bloom.bloom_requirements_pdf(png)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    CompanyLogoTest().run()
