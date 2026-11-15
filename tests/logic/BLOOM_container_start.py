"""
* @file     ${tests/logic/BLOOM_container_start.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The image starts as root only for preparation and hands every process to appuser.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests start.sh, supervisord.conf and the Dockerfile.
"""

from tests.logic.container_start import ContainerStartBase


class ContainerStartTest(ContainerStartBase):

    def setUpClass(self):
        super().setUpClass()
        script = self.parameters.START_SCRIPT
        self.tc_start = self.bloom.bloom_read_repo_text(script)
        self.tc_start_lines = self.bloom.bloom_read_repo_lines(script)
        self.tc_cloudron = self.bloom.bloom_read_repo_block(
            script, self.parameters.START_CLOUDRON_IF, self.parameters.START_ELSE
        )
        self.tc_local = self.bloom.bloom_read_repo_block(
            script, self.parameters.START_ELSE, self.parameters.START_FI
        )
        self.tc_supervisord = self.bloom.bloom_read_repo_lines(self.parameters.SUPERVISORD_CONF)
        self.tc_dockerfile = self.bloom.bloom_read_repo_text(self.parameters.DOCKERFILE)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ContainerStartTest().run()
