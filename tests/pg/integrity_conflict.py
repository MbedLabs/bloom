"""
* @file     ${tests/pg/integrity_conflict.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the answer to a unique constraint violated on flush.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the constraint conflict on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class IntegrityConflictBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_constraint_violation_is_answered_as_409(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"status": self.tc_answer.status, "body": self.tc_answer.body})
        self.assertEqual(
            self.tc_answer.status,
            self.parameters.STATUS_CONFLICT,
            msg=self.parameters.MSG_CONFLICT_STATUS,
            abort_on_fail=False,
        )

    def bud_detail_says_it_already_exists(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        detail = self.tc_answer.body[self.parameters.CONFLICT_DETAIL_KEY]
        self.print_variables({"detail": detail})
        self.assertIn(
            self.parameters.CONFLICT_PHRASE,
            detail,
            msg=self.parameters.MSG_CONFLICT_PHRASE,
            abort_on_fail=False,
        )

    def bud_answer_carries_a_request_id(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        request_id = self.tc_answer.body[self.parameters.CONFLICT_REQUEST_ID_KEY]
        self.print_variables({"request id": request_id})
        self.assertTrue(
            request_id, msg=self.parameters.MSG_CONFLICT_REQUEST_ID, abort_on_fail=False
        )

    def bud_detail_quotes_the_request_id(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        request_id = self.tc_answer.body[self.parameters.CONFLICT_REQUEST_ID_KEY]
        detail = self.tc_answer.body[self.parameters.CONFLICT_DETAIL_KEY]
        self.print_variables({"request id": request_id, "detail": detail})
        self.assertIn(
            request_id, detail, msg=self.parameters.MSG_CONFLICT_QUOTES_ID, abort_on_fail=False
        )

    def bud_answer_hides_the_constraint(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"answer": self.tc_answer.text})
        for leak in self.parameters.CONFLICT_LEAKS:
            self.assertNotIn(
                leak,
                self.tc_answer.text,
                msg=self.parameters.MSG_CONFLICT_NO_LEAK.format(leak=leak),
                abort_on_fail=False,
            )
