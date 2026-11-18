"""
* @file     ${tests/logic/BLOOM_export.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The requirements export writes CSV and PDF, the traceability export marks coverage, and a missing project is refused.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the exports of a project with one verified and one uncovered requirement.
"""

from tests.logic.export import ExportBase


class ExportTest(ExportBase):

    def setUpClass(self):
        super().setUpClass()
        self.project = self.bloom.bloom_seed_export_requirements()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ExportTest().run()
