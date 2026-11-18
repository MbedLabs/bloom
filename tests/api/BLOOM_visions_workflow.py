"""
* @file     ${tests/api/BLOOM_visions_workflow.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A Vision is approved, corrected and revised like a Specification.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests one vision on the full application with four administrators; the steps follow one another.
"""

from tests.api.visions_workflow import VisionsWorkflowBase


class VisionsWorkflowTest(VisionsWorkflowBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_workflow_api()
        self.bloom.bloom_new_workflow_world()
        self.vision = self.bloom.bloom_add_record("Document", **self.parameters.VISW_VISION)
        self.path = f"/api/artefacts/document/{self.vision}"

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    VisionsWorkflowTest().run()
