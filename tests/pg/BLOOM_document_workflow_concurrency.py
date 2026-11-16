"""
* @file     ${tests/pg/BLOOM_document_workflow_concurrency.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Two first reads of an artefact's workflow at once store one workflow.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the application on a new PostgreSQL database, with both reads held until each has looked the workflow up.
"""

from tests.pg.document_workflow_concurrency import DocumentWorkflowConcurrencyBase


class DocumentWorkflowConcurrencyTest(DocumentWorkflowConcurrencyBase):

    def setUpClass(self):
        super().setUpClass()
        self.postgres = self.bloom.bloom_use_postgres()
        if not self.postgres:
            return
        self.bloom.bloom_start_main_api()
        self.user_id = self.bloom.bloom_add_admin(
            self.parameters.WORKFLOW_RACE_EMAIL, self.parameters.API_PASSWORD
        )
        project = self.bloom.bloom_create_project(self.parameters.WORKFLOW_RACE_PREFIX)
        requirement = self.bloom.bloom_add_requirements(
            project, [self.parameters.WORKFLOW_RACE_REQ_ID], created_by_id=self.user_id
        )[0]
        self.bloom.bloom_act_as(self.user_id)
        self.replies = self.bloom.bloom_race_first_workflow_reads(requirement)
        self.workflows = self.bloom.bloom_list_workflows()
        self.later = self.bloom.bloom_read_workflow(requirement)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DocumentWorkflowConcurrencyTest().run()
