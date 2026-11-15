"""
* @file     ${tests/logic/BLOOM_attachment_stream.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A streamed attachment keeps its bytes and checksum; failed streams leave no file.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     This module tests a complete, an oversize and two interrupted streams.
"""

import asyncio

from tests.logic.attachment_stream import AttachmentStreamBase


class AttachmentStreamTest(AttachmentStreamBase):

    def setUpClass(self):
        super().setUpClass()
        payload = self.parameters.STREAM_PAYLOAD
        self.tc_complete = self.bloom.bloom_stream_attachment(payload, len(payload))
        self.tc_oversize = self.bloom.bloom_stream_attachment(
            self.parameters.STREAM_OVERSIZE, self.parameters.STREAM_OVERSIZE_LIMIT
        )
        errors = {"OSError": OSError, "CancelledError": asyncio.CancelledError}
        self.tc_interrupted = {
            name: self.bloom.bloom_stream_attachment(
                self.parameters.STREAM_FIRST_CHUNK,
                self.parameters.STREAM_INTERRUPT_LIMIT,
                interrupt=errors[name],
            )
            for name in self.parameters.STREAM_INTERRUPTIONS
        }

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AttachmentStreamTest().run()
