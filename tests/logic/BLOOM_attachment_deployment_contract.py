"""
* @file     ${tests/logic/BLOOM_attachment_deployment_contract.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Attachment evidence survives a replacement of the Bloom application container.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests the compose file, the Dockerfile and the example environment.
"""

from tests.logic.attachment_deployment_contract import AttachmentDeploymentContractBase


class AttachmentDeploymentContractTest(AttachmentDeploymentContractBase):

    def setUpClass(self):
        super().setUpClass()
        self.compose = self.bloom.bloom_read_compose_service(self.parameters.COMPOSE_SERVICE)
        self.dockerfile = self.bloom.bloom_read_repo_lines_with(
            self.parameters.DOCKERFILE, self.parameters.ATTACHMENT_WORDS
        )
        self.example = self.bloom.bloom_read_repo_lines_with(
            self.parameters.ENV_EXAMPLE, self.parameters.ATTACHMENT_WORDS
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AttachmentDeploymentContractTest().run()
