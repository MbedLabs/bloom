"""
* @file     ${tests/logic/BLOOM_attachment_cleanup.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Only old attachment files that nothing references are removed, and the application start runs the reconciliation.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the reconciliation on a scratch attachment folder.
"""

from tests.logic.attachment_cleanup import AttachmentCleanupBase


class AttachmentCleanupTest(AttachmentCleanupBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AttachmentCleanupTest().run()
