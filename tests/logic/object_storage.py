"""
* @file     ${tests/logic/object_storage.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests attachment storage in an S3 bucket.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the S3 attachment storage.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ObjectStorageBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_a_file_round_trips_through_the_bucket(self):
        self.bloom.bloom_new_object_store()
        values = self.parameters
        path = self.bloom.bloom_write_local_file("a.txt")
        self.bloom.bloom_persist(path, "a.txt")
        self.assertEqual(
            (
                path.exists(),
                self.bloom.bloom_bucket_keys(),
                self.bloom.bloom_bucket_content_type("bloom/a.txt"),
            ),
            (True, ["bloom/a.txt"], "text/plain"),
            msg=values.MSG_OBJ_PERSIST,
            abort_on_fail=False,
        )
        self.assertEqual(
            (
                self.bloom.bloom_fetch_object("a.txt"),
                self.bloom.bloom_list_objects(),
                self.bloom.bloom_object_size("a.txt"),
                self.bloom.bloom_object_size("nope.txt"),
                self.bloom.bloom_bucket_answers(),
            ),
            (values.OBJ_CONTENT, ["a.txt"], len(values.OBJ_CONTENT), None, True),
            msg=values.MSG_OBJ_READ,
            abort_on_fail=False,
        )
        self.bloom.bloom_remove_attachment("a.txt")
        self.assertEqual(
            (
                self.bloom.bloom_bucket_keys(),
                path.exists(),
                self.bloom.bloom_remove_attachment("a.txt"),
            ),
            ([], False, None),
            msg=values.MSG_OBJ_REMOVE,
            abort_on_fail=False,
        )

    def bud_without_the_mirror_the_local_file_goes(self):
        self.bloom.bloom_new_object_store(mirror=False)
        path = self.bloom.bloom_write_local_file("b.txt")
        self.bloom.bloom_persist(path, "b.txt")
        self.assertEqual(
            (path.exists(), self.bloom.bloom_bucket_keys()),
            (False, ["bloom/b.txt"]),
            msg=self.parameters.MSG_OBJ_NO_MIRROR,
            abort_on_fail=False,
        )

    def bud_a_refused_upload_leaves_nothing(self):
        self.bloom.bloom_new_object_store()
        self.bloom.bloom_set_storage(S3_BUCKET="no-such-bucket")
        path = self.bloom.bloom_write_local_file("c.txt")
        refused = self.bloom.bloom_persist(path, "c.txt")
        self.assertEqual(
            (refused, path.exists(), self.bloom.bloom_bucket_answers()),
            (self.parameters.STATUS_UNAVAILABLE, False, False),
            msg=self.parameters.MSG_OBJ_REFUSED,
            abort_on_fail=False,
        )

    def bud_local_storage_keeps_the_file_local(self):
        self.bloom.bloom_new_object_store(backend="local")
        path = self.bloom.bloom_write_local_file("d.txt")
        self.bloom.bloom_persist(path, "d.txt")
        self.assertEqual(
            (
                path.exists(),
                self.bloom.bloom_keeps_local_copy(),
                self.bloom.bloom_object_key("d.txt")[0],
            ),
            (True, True, "bloom/d.txt"),
            msg=self.parameters.MSG_OBJ_LOCAL,
            abort_on_fail=False,
        )

    def bud_a_download_streams_from_the_bucket_and_falls_back(self):
        self.bloom.bloom_new_object_store()
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_spec_document()
        values = self.parameters
        path = self.bloom.bloom_write_local_file("e.txt")
        self.bloom.bloom_persist(path, "e.txt")
        attachment = self.bloom.bloom_add_attachment_row(records.document, "e.txt")
        streamed = self.bloom.bloom_download_attachment(attachment, records.admin)
        self.assertEqual(
            (streamed.body, (streamed.disposition or "").startswith("attachment;")),
            (values.OBJ_CONTENT, True),
            msg=values.MSG_OBJ_DOWNLOAD,
            abort_on_fail=False,
        )
        self.bloom.bloom_delete_bucket_object("bloom/e.txt")
        fallback = self.bloom.bloom_download_attachment(attachment, records.admin)
        self.assertEqual(fallback.path, str(path), msg=values.MSG_OBJ_FALLBACK, abort_on_fail=False)
        path.unlink()
        gone = self.bloom.bloom_download_attachment(attachment, records.admin)
        self.assertEqual(
            gone.status, values.STATUS_UNAVAILABLE, msg=values.MSG_OBJ_GONE, abort_on_fail=False
        )

    def bud_the_cleanup_reconciles_the_bucket(self):
        self.bloom.bloom_new_object_store()
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_spec_document()
        for name in ("kept.txt", "orphan.txt"):
            self.bloom.bloom_persist(self.bloom.bloom_write_local_file(name), name)
        self.bloom.bloom_add_attachment_row(records.document, "kept.txt")
        self.bloom.bloom_add_attachment_row(records.document, "missing.txt")
        report = self.bloom.bloom_reconcile_stored_attachments(-60)
        self.print_variables({"missing": report.missing_files, "orphans": report.orphan_files})
        self.assertEqual(
            (self.bloom.bloom_bucket_keys(), report.missing_files, report.orphan_files),
            (["bloom/kept.txt"], 1, 2),
            msg=self.parameters.MSG_OBJ_RECONCILE,
            abort_on_fail=False,
        )
        self.bloom.bloom_set_storage(STORAGE_LOCAL_MIRROR=False)
        self.bloom.bloom_put_object(self.bloom.bloom_write_local_file("late.txt"), "late.txt")
        again = self.bloom.bloom_reconcile_stored_attachments(-60)
        self.assertEqual(
            (again.orphan_files, self.bloom.bloom_bucket_keys()),
            (1, ["bloom/kept.txt"]),
            msg=self.parameters.MSG_OBJ_RECONCILE_LATE,
            abort_on_fail=False,
        )

    def bud_the_migration_copies_once_and_checks_sizes(self):
        self.bloom.bloom_new_object_store()
        values = self.parameters
        self.bloom.bloom_write_local_file("m1.txt")
        self.bloom.bloom_write_local_file("m2.txt", values.OBJ_LONGER_CONTENT)
        self.bloom.bloom_write_local_file(".attachment-part.part")
        self.assertEqual(
            (self.bloom.bloom_migrate_to_s3(), self.bloom.bloom_bucket_keys()),
            ((2, 0, []), ["bloom/m1.txt", "bloom/m2.txt"]),
            msg=values.MSG_OBJ_MIGRATE,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.bloom.bloom_migrate_to_s3(),
            (0, 2, []),
            msg=values.MSG_OBJ_MIGRATE_AGAIN,
            abort_on_fail=False,
        )
        self.bloom.bloom_write_local_file("m3.txt")
        self.assertEqual(
            self.bloom.bloom_migrate_to_s3(wrong_size_for="m3.txt"),
            (0, 2, ["m3.txt"]),
            msg=values.MSG_OBJ_MIGRATE_SIZE,
            abort_on_fail=False,
        )

    def bud_the_migrate_command_reports_and_exits(self):
        self.bloom.bloom_new_object_store()
        values = self.parameters
        code, out, _ = self.bloom.bloom_storage_command(values.OBJ_MIGRATE, migrated=(1, 2, []))
        self.assertEqual(
            (code, "copied 1, already there 2, size mismatches 0" in out),
            (0, True),
            msg=values.MSG_OBJ_COMMAND_OK,
            abort_on_fail=False,
        )
        code, _, err = self.bloom.bloom_storage_command(
            values.OBJ_MIGRATE, migrated=(0, 0, ["x.txt"])
        )
        self.assertEqual(
            (code, "size mismatch: x.txt" in err),
            (1, True),
            msg=values.MSG_OBJ_COMMAND_MISMATCH,
            abort_on_fail=False,
        )
        self.bloom.bloom_set_storage(S3_BUCKET="")
        code, _, _ = self.bloom.bloom_storage_command(values.OBJ_MIGRATE, migrated=(0, 0, []))
        self.assertEqual(code, 2, msg=values.MSG_OBJ_COMMAND_NO_BUCKET, abort_on_fail=False)

    def bud_s3_storage_needs_a_bucket(self):
        _, refusal = self.bloom.bloom_s3_settings("")
        prefix, _ = self.bloom.bloom_s3_settings("b")
        self.assertEqual(
            ("needs S3_BUCKET" in (refusal or ""), prefix),
            (True, "bloom"),
            msg=self.parameters.MSG_OBJ_NEEDS_BUCKET,
            abort_on_fail=False,
        )

    def bud_the_client_takes_its_options_from_the_settings(self):
        values = self.parameters
        made = self.bloom.bloom_object_store_client(**values.OBJ_CLIENT_SETTINGS)
        self.assertEqual(
            made,
            (
                values.OBJ_CLIENT_SETTINGS["S3_ENDPOINT_URL"],
                values.OBJ_CLIENT_SETTINGS["S3_REGION"],
            ),
            msg=values.MSG_OBJ_CLIENT,
            abort_on_fail=False,
        )
        self.bloom.bloom_new_object_store()
        self.bloom.bloom_set_storage(S3_PREFIX="")
        self.assertEqual(
            self.bloom.bloom_object_key("f.txt"),
            ("f.txt", "f.txt"),
            msg=values.MSG_OBJ_NO_PREFIX,
            abort_on_fail=False,
        )
