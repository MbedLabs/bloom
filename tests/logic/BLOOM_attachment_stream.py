"""
* @file     ${tests/logic/BLOOM_attachment_stream.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A streamed attachment keeps its bytes and checksum; failed streams leave no file.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests a complete, an oversize and two interrupted streams.
"""

from tests.logic.attachment_stream import AttachmentStreamBase


class AttachmentStreamTest(AttachmentStreamBase):

    def setUpClass(self):
        super().setUpClass()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AttachmentStreamTest().run()
