"""
* @file     ${tests/logic/reqif_limits.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the limits on ReqIF uploads, archives and documents.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the ReqIF limits.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ReqifLimitsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_an_upload_at_the_request_limit_is_read(self):
        upload = self.bloom.bloom_read_reqif_upload(b"x" * 10, **self.parameters.RQL_STREAM_LIMITS)
        self.print_variables({"read calls": upload.read_calls})
        self.assertEqual(
            (upload.data, upload.read_calls > 1),
            (b"x" * 10, True),
            msg=self.parameters.MSG_RQL_AT_LIMIT,
            abort_on_fail=False,
        )

    def bud_an_upload_over_the_request_limit_stops_early(self):
        upload = self.bloom.bloom_read_reqif_upload(b"x" * 100, **self.parameters.RQL_STREAM_LIMITS)
        self.print_variables({"refusal": upload.refusal, "bytes read": upload.read_bytes})
        refusal = upload.refusal or ""
        self.assertEqual(
            ("request" in refusal, "25 MiB" in refusal, upload.read_bytes < 100),
            (True, True, True),
            msg=self.parameters.MSG_RQL_OVER_LIMIT,
            abort_on_fail=False,
        )

    def bud_an_archive_needs_exactly_one_reqif_member(self):
        for what, entries in self.parameters.RQL_WRONG_ARCHIVES:
            _, refusal = self.bloom.bloom_parse_reqif(self.bloom.bloom_reqif_archive(entries))
            self.assertIn(
                "exactly one",
                refusal or "",
                msg=self.parameters.MSG_RQL_ONE_MEMBER.format(what=what),
                abort_on_fail=False,
            )

    def bud_the_archive_entry_limit_is_enforced(self):
        archive = self.bloom.bloom_reqif_archive(self.parameters.RQL_THREE_ENTRIES)
        _, refusal = self.bloom.bloom_parse_reqif(archive, REQIF_MAX_ARCHIVE_ENTRIES=2)
        self.assertIn(
            "archive entries",
            refusal or "",
            msg=self.parameters.MSG_RQL_ENTRIES,
            abort_on_fail=False,
        )

    def bud_the_uncompressed_member_limit_is_enforced(self):
        archive = self.bloom.bloom_reqif_archive(self.parameters.RQL_ONE_ENTRY)
        _, refusal = self.bloom.bloom_parse_reqif(
            archive, REQIF_MAX_MEMBER_BYTES=len(self.parameters.RQL_MINIMAL) - 1
        )
        self.assertIn(
            "uncompressed",
            refusal or "",
            msg=self.parameters.MSG_RQL_MEMBER_SIZE,
            abort_on_fail=False,
        )

    def bud_the_compression_ratio_limit_is_enforced(self):
        archive = self.bloom.bloom_reqif_archive(self.parameters.RQL_PADDED_ENTRY, deflated=True)
        _, refusal = self.bloom.bloom_parse_reqif(archive, REQIF_MAX_COMPRESSION_RATIO=20)
        self.assertIn(
            "compression ratio",
            refusal or "",
            msg=self.parameters.MSG_RQL_RATIO,
            abort_on_fail=False,
        )

    def bud_an_encrypted_archive_member_is_refused(self):
        self.assertIn(
            "Encrypted",
            self.bloom.bloom_check_encrypted_member() or "",
            msg=self.parameters.MSG_RQL_ENCRYPTED,
            abort_on_fail=False,
        )

    def bud_the_parser_runs_in_a_worker(self):
        bundle, timed_out = self.bloom.bloom_parse_reqif_in_worker(self.parameters.RQL_MINIMAL, 10)
        self.assertEqual(
            (timed_out, set(bundle.objects) if bundle else None),
            (False, {"OBJ-1"}),
            msg=self.parameters.MSG_RQL_WORKER,
            abort_on_fail=False,
        )

    def bud_the_worker_is_stopped_at_the_deadline(self):
        _, timed_out = self.bloom.bloom_parse_reqif_in_worker(self.parameters.RQL_MINIMAL, 0)
        self.assertTrue(timed_out, msg=self.parameters.MSG_RQL_DEADLINE, abort_on_fail=False)

    def bud_the_object_limit_is_enforced(self):
        document = self.bloom.bloom_reqif_document(objects=self.parameters.RQL_THREE_OBJECTS)
        _, refusal = self.bloom.bloom_parse_reqif(document, REQIF_MAX_OBJECTS=2)
        self.assertIn(
            "object limit", refusal or "", msg=self.parameters.MSG_RQL_OBJECTS, abort_on_fail=False
        )

    def bud_the_relation_limit_is_enforced(self):
        document = self.bloom.bloom_reqif_document(
            objects=self.parameters.RQL_ONE_OBJECT, relations=self.parameters.RQL_TWO_RELATIONS
        )
        _, refusal = self.bloom.bloom_parse_reqif(document, REQIF_MAX_RELATIONS=1)
        self.assertIn(
            "relation limit",
            refusal or "",
            msg=self.parameters.MSG_RQL_RELATIONS,
            abort_on_fail=False,
        )

    def bud_the_hierarchy_depth_limit_is_enforced(self):
        document = self.bloom.bloom_reqif_document(hierarchy=self.parameters.RQL_THREE_LEVELS)
        _, refusal = self.bloom.bloom_parse_reqif(document, REQIF_MAX_HIERARCHY_DEPTH=2)
        self.assertIn(
            "hierarchy depth", refusal or "", msg=self.parameters.MSG_RQL_DEPTH, abort_on_fail=False
        )

    def bud_a_repeated_ancestor_is_refused_as_a_cycle(self):
        document = self.bloom.bloom_reqif_document(hierarchy=self.parameters.RQL_REPEATED_ANCESTOR)
        _, refusal = self.bloom.bloom_parse_reqif(document)
        self.assertIn(
            "cycle", refusal or "", msg=self.parameters.MSG_RQL_CYCLE, abort_on_fail=False
        )
