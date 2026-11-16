"""
* @file     ${tests/pg/document_workflow_concurrency.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests two first reads of one artefact's workflow at once.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the workflow read race on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class DocumentWorkflowConcurrencyBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_both_first_reads_are_answered_200(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"replies": [(reply.status, reply.body) for reply in self.replies]})
        self.assertEqual(
            [reply.status for reply in self.replies],
            [self.parameters.STATUS_OK] * 2,
            msg=self.parameters.MSG_WORKFLOW_RACE_READS,
            abort_on_fail=False,
        )

    def bud_one_workflow_is_stored(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"workflows": len(self.workflows)})
        self.assertEqual(
            len(self.workflows),
            1,
            msg=self.parameters.MSG_WORKFLOW_RACE_ONE,
            abort_on_fail=False,
        )

    def bud_stored_workflow_is_a_first_draft_of_the_creator(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        stored = self.workflows[0]
        self.print_variables(
            {
                "revision": stored.revision_number,
                "phase": stored.phase,
                "creator": stored.revision_creator_id,
            }
        )
        self.assertEqual(
            (stored.revision_number, stored.phase, stored.revision_creator_id),
            (
                self.parameters.WORKFLOW_RACE_FIRST_REVISION,
                self.parameters.STATUS_DRAFT,
                self.user_id,
            ),
            msg=self.parameters.MSG_WORKFLOW_RACE_STATE,
            abort_on_fail=False,
        )

    def bud_later_read_is_answered_200(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.later.status, "body": self.later.body})
        self.assertEqual(
            self.later.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_WORKFLOW_RACE_LATER,
            abort_on_fail=False,
        )

    def bud_later_read_shows_the_revision_of_the_first_reads(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        key = self.parameters.WORKFLOW_RACE_REVISION_KEY
        self.assertEqual(
            (self.later.body[key], self.replies[0].body[key]),
            (
                self.parameters.WORKFLOW_RACE_FIRST_REVISION,
                self.parameters.WORKFLOW_RACE_FIRST_REVISION,
            ),
            msg=self.parameters.MSG_WORKFLOW_RACE_REVISION,
            abort_on_fail=False,
        )

    def bud_later_read_names_the_creator(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        creator = self.later.body[self.parameters.WORKFLOW_RACE_CREATOR_KEY]
        self.assertEqual(
            creator[self.parameters.WORKFLOW_RACE_ID_KEY],
            self.user_id,
            msg=self.parameters.MSG_WORKFLOW_RACE_CREATOR,
            abort_on_fail=False,
        )
