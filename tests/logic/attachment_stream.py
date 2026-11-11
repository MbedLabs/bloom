"""
* @file     ${tests/logic/attachment_stream.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests streamed attachment storage: limits, checksums and cleanup.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the attachment stream.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class AttachmentStreamBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_stream_keeps_content_size_and_checksum(self):
        stored = self.tc_complete.stored
        self.print_variables(
            {
                "content": self.tc_complete.content,
                "size": getattr(stored, "size_bytes", None),
                "sha256": getattr(stored, "sha256", None),
                "parts": self.tc_complete.parts,
            }
        )
        self.assertEqual(
            self.tc_complete.content,
            self.parameters.STREAM_PAYLOAD,
            msg=self.parameters.MSG_STREAM_CONTENT,
            abort_on_fail=False,
        )
        self.assertEqual(
            getattr(stored, "size_bytes", None),
            len(self.parameters.STREAM_PAYLOAD),
            msg=self.parameters.MSG_STREAM_SIZE,
            abort_on_fail=False,
        )
        self.assertEqual(
            getattr(stored, "sha256", None),
            self.parameters.STREAM_SHA256,
            msg=self.parameters.MSG_STREAM_SHA,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.tc_complete.parts,
            self.parameters.STREAM_NO_FILES,
            msg=self.parameters.MSG_STREAM_NO_PARTS,
            abort_on_fail=False,
        )

    def bud_oversize_stream_is_refused_and_removed(self):
        self.print_variables(
            {
                "status": self.tc_oversize.status,
                "content": self.tc_oversize.content,
                "files": self.tc_oversize.files,
            }
        )
        self.assertEqual(
            self.tc_oversize.status,
            self.parameters.STATUS_TOO_LARGE,
            msg=self.parameters.MSG_STREAM_TOO_LARGE,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.tc_oversize.content,
            None,
            msg=self.parameters.MSG_STREAM_NO_TARGET,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.tc_oversize.files,
            self.parameters.STREAM_NO_FILES,
            msg=self.parameters.MSG_STREAM_CLEAN,
            abort_on_fail=False,
        )

    def bud_interrupted_stream_is_removed(self):
        for name, outcome in self.tc_interrupted.items():
            self.print_variables(
                {"interruption": name, "error": outcome.error, "reads": outcome.reads}
            )
            self.assertEqual(
                outcome.error, name, msg=self.parameters.MSG_STREAM_ERROR, abort_on_fail=False
            )
            self.assertEqual(
                outcome.reads,
                self.parameters.STREAM_INTERRUPTED_READS,
                msg=self.parameters.MSG_STREAM_READS,
                abort_on_fail=False,
            )
            self.assertEqual(
                outcome.files,
                self.parameters.STREAM_NO_FILES,
                msg=self.parameters.MSG_STREAM_CLEAN,
                abort_on_fail=False,
            )
