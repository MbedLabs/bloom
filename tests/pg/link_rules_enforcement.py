"""
* @file     ${tests/pg/link_rules_enforcement.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the link rules the database enforces after the migration.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the link rule enforcement on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class LinkRulesEnforcementBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_migrations_reach_the_revision_before(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"alembic": self.tc_before[1][-300:]})
        self.assertEqual(
            self.tc_before[0],
            0,
            msg=self.parameters.MSG_MIGRATION_BEFORE,
            abort_on_fail=False,
        )

    def bud_migrations_reach_head(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"alembic": self.tc_upgrade[1][-300:]})
        self.assertEqual(
            self.tc_upgrade[0],
            0,
            msg=self.parameters.MSG_MIGRATION_HEAD,
            abort_on_fail=False,
        )

    def bud_upgrade_leaves_the_constraint_unvalidated(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"validated": self.tc_validated_after_upgrade})
        self.assertEqual(
            self.tc_validated_after_upgrade,
            False,
            msg=self.parameters.MSG_LINK_UNVALIDATED,
            abort_on_fail=False,
        )

    def bud_upgrade_keeps_the_forbidden_link(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"link before": self.tc_old_link, "link after": self.tc_kept_link})
        self.assertEqual(
            self.tc_kept_link,
            self.tc_old_link,
            msg=self.parameters.MSG_LINK_KEPT,
            abort_on_fail=False,
        )

    def bud_new_forbidden_triples_are_refused_by_the_constraint(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        for triple, error in zip(self.parameters.LINK_REJECTED, self.tc_rejected):
            self.print_variables({"triple": triple, "error": (error or "")[:160]})
            self.assertIn(
                self.parameters.LINK_CONSTRAINT,
                error or "",
                msg=self.parameters.MSG_LINK_REJECTED.format(triple=triple),
                abort_on_fail=False,
            )

    def bud_new_allowed_triples_are_stored(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        for triple, link_id in zip(self.parameters.LINK_ACCEPTED, self.tc_accepted):
            self.assertTrue(
                link_id,
                msg=self.parameters.MSG_LINK_ACCEPTED.format(triple=triple),
                abort_on_fail=False,
            )

    def bud_allowed_table_equals_the_code_rules(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {
                "triples in the database": len(self.tc_table_triples),
                "triples in the code": len(self.tc_code_triples),
            }
        )
        self.assertEqual(
            self.tc_table_triples,
            self.tc_code_triples,
            msg=self.parameters.MSG_LINK_TABLE_IS_CODE,
            abort_on_fail=False,
        )

    def bud_check_answers_1_while_a_forbidden_link_exists(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"report": self.tc_refused_check.report})
        self.assertEqual(
            self.tc_refused_check.exit_code,
            self.parameters.LINK_CHECK_REFUSED,
            msg=self.parameters.MSG_LINK_CHECK_REFUSED,
            abort_on_fail=False,
        )

    def bud_report_names_the_forbidden_link(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        key = self.parameters.LINK_REPORT_TABLE_KEY
        rows = [
            row for row in self.tc_refused_check.report if row[key] == self.parameters.LINK_TABLE
        ]
        self.assertEqual(
            [(row["id"], row["role"]) for row in rows],
            [(self.tc_old_link, self.parameters.LINK_FORBIDDEN[2])],
            msg=self.parameters.MSG_LINK_REPORT_INVALID,
            abort_on_fail=False,
        )

    def bud_report_maps_the_legacy_requirement_link(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        key = self.parameters.LINK_REPORT_TABLE_KEY
        table = self.parameters.LINK_LEGACY_TABLE
        rows = [row for row in self.tc_refused_check.report if row[key] == table]
        self.assertEqual(
            [(row["link_type"], row["mapped_role"]) for row in rows],
            [self.parameters.LINK_LEGACY],
            msg=self.parameters.MSG_LINK_REPORT_LEGACY,
            abort_on_fail=False,
        )

    def bud_refused_check_leaves_the_constraint_unvalidated(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.tc_validated_after_refusal,
            False,
            msg=self.parameters.MSG_LINK_STILL_UNVALIDATED,
            abort_on_fail=False,
        )

    def bud_check_answers_0_once_the_link_is_allowed(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"report": self.tc_passed_check.report})
        self.assertEqual(
            self.tc_passed_check.exit_code,
            self.parameters.LINK_CHECK_PASSED,
            msg=self.parameters.MSG_LINK_CHECK_PASSED,
            abort_on_fail=False,
        )

    def bud_passed_check_validates_the_constraint(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.tc_validated_after_pass,
            True,
            msg=self.parameters.MSG_LINK_VALIDATED,
            abort_on_fail=False,
        )

    def bud_no_link_is_lost(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"requirement links, artefact links": self.tc_link_counts})
        self.assertEqual(
            self.tc_link_counts,
            (1, 1),
            msg=self.parameters.MSG_LINK_COUNTS,
            abort_on_fail=False,
        )
