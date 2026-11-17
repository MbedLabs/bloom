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

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ContainerStartTest().run()
