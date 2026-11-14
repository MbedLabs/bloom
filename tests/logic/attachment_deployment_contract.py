"""
* @file     ${tests/logic/attachment_deployment_contract.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that attachments live on a volume outside the app container.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the attachment deployment contract.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class AttachmentDeploymentContractBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_compose_sets_the_attachment_directory(self):
        environment = self.tc_compose.service["environment"]
        self.print_variables({"environment": environment})
        self.assertEqual(
            environment.get(self.parameters.ATTACHMENT_DIR_VARIABLE),
            self.parameters.ATTACHMENT_DIR,
            msg=self.parameters.MSG_ATTACHMENT_DIR_SET,
            abort_on_fail=False,
        )

    def bud_compose_mounts_the_attachment_volume(self):
        volumes = self.tc_compose.service["volumes"]
        self.print_variables({"volumes": volumes})
        self.assertIn(
            self.parameters.ATTACHMENT_MOUNT,
            volumes,
            msg=self.parameters.MSG_ATTACHMENT_MOUNTED,
            abort_on_fail=False,
        )

    def bud_compose_declares_the_attachment_volume(self):
        declared = list(self.tc_compose.volumes)
        self.print_variables({"declared": declared})
        self.assertIn(
            self.parameters.ATTACHMENT_VOLUME,
            declared,
            msg=self.parameters.MSG_ATTACHMENT_VOLUME_DECLARED,
            abort_on_fail=False,
        )

    def bud_image_creates_the_mountpoint(self):
        self.print_variables({"line": self.parameters.ATTACHMENT_MKDIR})
        self.assertIn(
            self.parameters.ATTACHMENT_MKDIR,
            self.tc_dockerfile,
            msg=self.parameters.MSG_ATTACHMENT_MKDIR,
            abort_on_fail=False,
        )

    def bud_image_gives_the_app_to_appuser(self):
        self.print_variables({"line": self.parameters.ATTACHMENT_CHOWN})
        self.assertIn(
            self.parameters.ATTACHMENT_CHOWN,
            self.tc_dockerfile,
            msg=self.parameters.MSG_ATTACHMENT_CHOWN,
            abort_on_fail=False,
        )

    def bud_example_documents_the_directory(self):
        self.print_variables({"line": self.parameters.ATTACHMENT_EXAMPLE_LINE})
        self.assertIn(
            self.parameters.ATTACHMENT_EXAMPLE_LINE,
            self.tc_example,
            msg=self.parameters.MSG_ATTACHMENT_EXAMPLE,
            abort_on_fail=False,
        )
