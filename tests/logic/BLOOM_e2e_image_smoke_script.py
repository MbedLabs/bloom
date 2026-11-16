"""
* @file     ${tests/logic/BLOOM_e2e_image_smoke_script.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The image smoke script passes the admin name as one argument and a valid project payload.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     This module tests the script against a fake docker that stops it at the app container.
"""

from tests.logic.e2e_image_smoke_script import E2eImageSmokeScriptBase


class E2eImageSmokeScriptTest(E2eImageSmokeScriptBase):

    def setUpClass(self):
        super().setUpClass()
        self.docker_calls = self.bloom.bloom_run_smoke_script_with_fake_docker(
            self.parameters.SMOKE_IMAGE
        )
        self.payload = self.bloom.bloom_read_smoke_project_payload()
        self.validated = (
            self.bloom.bloom_validate_project_payload(self.payload) if self.payload else None
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    E2eImageSmokeScriptTest().run()
