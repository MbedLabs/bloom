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
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"alembic": self.before[1][-300:]})
        self.assertEqual(
            self.before[0], 0, msg=self.parameters.MSG_MIGRATION_BEFORE, abort_on_fail=False
        )

    def bud_migrations_reach_head(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        self.print_variables({"alembic": output[-300:]})
        self.assertEqual(code, 0, msg=self.parameters.MSG_MIGRATION_HEAD, abort_on_fail=False)

    def bud_upgrade_leaves_the_constraint_unvalidated(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        validated = self.bloom.bloom_link_constraint_validated()
        self.print_variables({"validated": validated})
        self.assertEqual(
            validated, False, msg=self.parameters.MSG_LINK_UNVALIDATED, abort_on_fail=False
        )

    def bud_upgrade_keeps_the_forbidden_link(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        kept = self.bloom.bloom_first_link_id()
        self.print_variables({"link before": self.old_link, "link after": kept})
        self.assertEqual(
            kept, self.old_link, msg=self.parameters.MSG_LINK_KEPT, abort_on_fail=False
        )

    def bud_new_forbidden_triples_are_refused_by_the_constraint(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        for triple in self.parameters.LINK_REJECTED:
            error = self.bloom.bloom_insert_link(
                self.project, *triple, self.parameters.LINK_NEW_ENDS, keep=False
            ).error
            self.print_variables({"triple": triple, "error": (error or "")[:160]})
            self.assertIn(
                self.parameters.LINK_CONSTRAINT,
                error or "",
                msg=self.parameters.MSG_LINK_REJECTED.format(triple=triple),
                abort_on_fail=False,
            )

    def bud_new_allowed_triples_are_stored(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        for triple in self.parameters.LINK_ACCEPTED:
            link_id = self.bloom.bloom_insert_link(
                self.project, *triple, self.parameters.LINK_NEW_ENDS, keep=False
            ).id
            self.assertTrue(
                link_id,
                msg=self.parameters.MSG_LINK_ACCEPTED.format(triple=triple),
                abort_on_fail=False,
            )

    def bud_allowed_table_equals_the_code_rules(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        table_triples = self.bloom.bloom_read_allowed_link_triples()
        code_triples = self.bloom.bloom_code_link_triples()
        self.print_variables(
            {
                "triples in the database": len(table_triples),
                "triples in the code": len(code_triples),
            }
        )
        self.assertEqual(
            table_triples,
            code_triples,
            msg=self.parameters.MSG_LINK_TABLE_IS_CODE,
            abort_on_fail=False,
        )

    def bud_check_answers_1_while_a_forbidden_link_exists(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        check = self.bloom.bloom_check_link_rules()
        self.print_variables({"report": check.report})
        self.assertEqual(
            check.exit_code,
            self.parameters.LINK_CHECK_REFUSED,
            msg=self.parameters.MSG_LINK_CHECK_REFUSED,
            abort_on_fail=False,
        )

    def bud_report_names_the_forbidden_link(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        key = self.parameters.LINK_REPORT_TABLE_KEY
        rows = [
            row
            for row in self.bloom.bloom_check_link_rules().report
            if row[key] == self.parameters.LINK_TABLE
        ]
        self.assertEqual(
            [(row["id"], row["role"]) for row in rows],
            [(self.old_link, self.parameters.LINK_FORBIDDEN[2])],
            msg=self.parameters.MSG_LINK_REPORT_INVALID,
            abort_on_fail=False,
        )

    def bud_report_maps_the_legacy_requirement_link(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        key = self.parameters.LINK_REPORT_TABLE_KEY
        rows = [
            row
            for row in self.bloom.bloom_check_link_rules().report
            if row[key] == self.parameters.LINK_LEGACY_TABLE
        ]
        self.assertEqual(
            [(row["link_type"], row["mapped_role"]) for row in rows],
            [self.parameters.LINK_LEGACY],
            msg=self.parameters.MSG_LINK_REPORT_LEGACY,
            abort_on_fail=False,
        )

    def bud_refused_check_leaves_the_constraint_unvalidated(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.bloom.bloom_link_constraint_validated(),
            False,
            msg=self.parameters.MSG_LINK_STILL_UNVALIDATED,
            abort_on_fail=False,
        )

    def bud_check_answers_0_once_the_link_is_allowed(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.bloom.bloom_set_link_role(self.old_link, self.parameters.LINK_CORRECTED_ROLE)
        check = self.bloom.bloom_check_link_rules()
        self.print_variables({"report": check.report})
        self.assertEqual(
            check.exit_code,
            self.parameters.LINK_CHECK_PASSED,
            msg=self.parameters.MSG_LINK_CHECK_PASSED,
            abort_on_fail=False,
        )

    def bud_passed_check_validates_the_constraint(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.bloom.bloom_link_constraint_validated(),
            True,
            msg=self.parameters.MSG_LINK_VALIDATED,
            abort_on_fail=False,
        )

    def bud_no_link_is_lost(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        counts = self.bloom.bloom_count_links()
        self.print_variables({"requirement links, artefact links": counts})
        self.assertEqual(counts, (1, 1), msg=self.parameters.MSG_LINK_COUNTS, abort_on_fail=False)
