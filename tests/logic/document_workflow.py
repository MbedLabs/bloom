"""
* @file     ${tests/logic/document_workflow.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the storage guards of the controlled document workflow.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the controlled workflow storage.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class DocumentWorkflowBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_an_unguarded_write_to_approved_content_is_refused_409(self):
        for kind in self.parameters.DWF_CONTROLLED_KINDS:
            self.bloom.bloom_new_database()
            self.bloom.bloom_seed_workflow_author()
            self.assertEqual(
                self.bloom.bloom_overwrite_approved(kind),
                self.parameters.STATUS_CONFLICT,
                msg=self.parameters.MSG_DWF_OVERWRITE.format(kind=kind),
                abort_on_fail=False,
            )

    def bud_a_direct_approval_is_refused_409(self):
        self.bloom.bloom_new_database()
        self.bloom.bloom_seed_workflow_author()
        self.assertEqual(
            self.bloom.bloom_approve_without_workflow(),
            self.parameters.STATUS_CONFLICT,
            msg=self.parameters.MSG_DWF_DIRECT_APPROVAL,
            abort_on_fail=False,
        )

    def bud_a_new_change_request_starts_as_draft(self):
        self.bloom.bloom_new_database()
        self.bloom.bloom_seed_workflow_author()
        self.assertEqual(
            self.bloom.bloom_new_change_request_status(),
            "Draft",
            msg=self.parameters.MSG_DWF_CHANGE_DEFAULT,
            abort_on_fail=False,
        )

    def bud_an_unguarded_child_of_an_approved_parent_is_refused_409(self):
        for child in self.parameters.DWF_CHILDREN:
            self.bloom.bloom_new_database()
            self.bloom.bloom_seed_workflow_author()
            self.assertEqual(
                self.bloom.bloom_add_child_to_approved(child),
                self.parameters.STATUS_CONFLICT,
                msg=self.parameters.MSG_DWF_CHILD.format(child=child),
                abort_on_fail=False,
            )

    def bud_the_snapshot_keeps_the_whole_document(self):
        self.bloom.bloom_new_database()
        self.bloom.bloom_seed_workflow_author()
        snapshot = self.bloom.bloom_snapshot_draft_document()
        self.print_variables({"snapshot": snapshot})
        self.assertEqual(
            snapshot,
            ("Approved body", "internal", [1], "Section body", "approved/proof", None, "Draft"),
            msg=self.parameters.MSG_DWF_SNAPSHOT,
            abort_on_fail=False,
        )

    def bud_an_execution_result_keeps_the_content_hash(self):
        self.bloom.bloom_new_database()
        self.bloom.bloom_seed_workflow_author()
        self.assertEqual(
            self.bloom.bloom_execution_result_changes_hash(),
            False,
            msg=self.parameters.MSG_DWF_EXECUTION,
            abort_on_fail=False,
        )

    def bud_capturing_a_revision_is_repeatable_and_its_file_is_fixed(self):
        self.bloom.bloom_new_database()
        self.bloom.bloom_seed_workflow_author()
        captured, overwrite = self.bloom.bloom_capture_revision_twice()
        self.assertEqual(
            captured,
            (True, None, None, None, "approved/proof"),
            msg=self.parameters.MSG_DWF_CAPTURE,
            abort_on_fail=False,
        )
        self.assertEqual(
            overwrite,
            self.parameters.STATUS_CONFLICT,
            msg=self.parameters.MSG_DWF_FILE_REF,
            abort_on_fail=False,
        )

    def bud_an_approved_archive_cannot_be_changed_409(self):
        for operation in self.parameters.DWF_ARCHIVE_OPERATIONS:
            self.bloom.bloom_new_database()
            self.bloom.bloom_seed_workflow_author()
            self.assertEqual(
                self.bloom.bloom_change_approved_archive(operation),
                self.parameters.STATUS_CONFLICT,
                msg=self.parameters.MSG_DWF_ARCHIVE.format(operation=operation),
                abort_on_fail=False,
            )

    def bud_a_content_edit_in_review_returns_to_draft(self):
        self.bloom.bloom_new_database()
        self.bloom.bloom_seed_workflow_author()
        self.assertEqual(
            self.bloom.bloom_edit_content_in_review(),
            ("Draft", "Draft", "superseded", 1, True, None),
            msg=self.parameters.MSG_DWF_REVIEW_EDIT,
            abort_on_fail=False,
        )

    def bud_a_new_revision_keeps_the_archive_and_the_baseline(self):
        self.bloom.bloom_new_database()
        self.bloom.bloom_seed_workflow_author()
        self.assertEqual(
            self.bloom.bloom_revise_approved_requirement(),
            ("Next draft", "Original", {"title": "Frozen baseline"}),
            msg=self.parameters.MSG_DWF_REVISION,
            abort_on_fail=False,
        )

    def bud_an_approved_change_request_stays_frozen_409(self):
        self.bloom.bloom_new_database()
        self.bloom.bloom_seed_workflow_author()
        self.assertEqual(
            self.bloom.bloom_reopen_approved_change_with_permit(),
            self.parameters.STATUS_CONFLICT,
            msg=self.parameters.MSG_DWF_CHANGE_FROZEN,
            abort_on_fail=False,
        )

    def bud_an_unsupported_status_gets_no_workflow(self):
        for kind, status in self.parameters.DWF_UNSUPPORTED:
            self.bloom.bloom_new_database()
            self.bloom.bloom_seed_workflow_author()
            self.assertEqual(
                self.bloom.bloom_workflow_of_unsupported_status(kind, status),
                (self.parameters.STATUS_CONFLICT, None, status, None),
                msg=self.parameters.MSG_DWF_UNSUPPORTED.format(kind=kind, status=status),
                abort_on_fail=False,
            )

    def bud_a_risk_record_is_written_without_a_workflow(self):
        self.bloom.bloom_new_database()
        self.bloom.bloom_seed_workflow_author()
        self.assertEqual(
            self.bloom.bloom_update_risk_record(),
            (None, "Open"),
            msg=self.parameters.MSG_DWF_RISK,
            abort_on_fail=False,
        )

    def bud_a_scope_change_in_review_returns_to_draft(self):
        for scope in self.parameters.DWF_SCOPES:
            self.bloom.bloom_new_database()
            self.bloom.bloom_seed_workflow_author()
            self.assertEqual(
                self.bloom.bloom_change_scope_in_review(scope),
                ("Draft", "Draft", "superseded", True),
                msg=self.parameters.MSG_DWF_SCOPE.format(scope=scope),
                abort_on_fail=False,
            )

    def bud_an_approved_scope_change_keeps_the_archived_scope(self):
        self.bloom.bloom_new_database()
        self.bloom.bloom_seed_workflow_author()
        archived, transport_unchanged = self.bloom.bloom_change_scope_of_approved()
        self.assertEqual(
            archived,
            ("internal", "Internal"),
            msg=self.parameters.MSG_DWF_APPROVED_SCOPE,
            abort_on_fail=False,
        )
        self.assertTrue(
            transport_unchanged, msg=self.parameters.MSG_DWF_TRANSPORT, abort_on_fail=False
        )

    def bud_legacy_concept_and_protocol_ids_are_controlled(self):
        self.assertEqual(
            self.bloom.bloom_legacy_identities(),
            (("test-concept", "CPT"), ("document", "PRT"), True, True),
            msg=self.parameters.MSG_DWF_ALIASES,
            abort_on_fail=False,
        )

    def bud_changing_the_kind_of_an_approved_document_is_refused_409(self):
        self.bloom.bloom_new_database()
        self.bloom.bloom_seed_workflow_author()
        self.assertEqual(
            self.bloom.bloom_change_kind_of_approved_document(),
            self.parameters.STATUS_CONFLICT,
            msg=self.parameters.MSG_DWF_KIND,
            abort_on_fail=False,
        )

    def bud_an_unguarded_write_in_review_returns_to_draft(self):
        for change in self.parameters.DWF_REVIEW_WRITES:
            self.bloom.bloom_new_database()
            self.bloom.bloom_seed_workflow_author()
            self.assertEqual(
                self.bloom.bloom_write_in_review_without_workflow(change),
                ("Draft", "Draft", "superseded", 1),
                msg=self.parameters.MSG_DWF_REVIEW_WRITE.format(change=change),
                abort_on_fail=False,
            )

    def bud_a_prepared_scope_edit_fits_review_and_approved(self):
        self.bloom.bloom_new_database()
        self.bloom.bloom_seed_workflow_author()
        self.assertEqual(
            self.bloom.bloom_prepared_scope_edits(),
            ("Draft", "Draft", "Approved"),
            msg=self.parameters.MSG_DWF_PREPARED,
            abort_on_fail=False,
        )
