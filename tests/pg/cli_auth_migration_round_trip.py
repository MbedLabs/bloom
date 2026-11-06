"""
* @file     ${tests/pg/cli_auth_migration_round_trip.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the CLI session migration up, down and up again on PostgreSQL.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the CLI session migration round trip.
"""

from tests.bloom_test_base import BloomTestCase


class CliAuthMigrationRoundTripBase(BloomTestCase):

    def bud_every_alembic_command_succeeds(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        for code, output in self.tc_commands:
            if code:
                self.log_info(output)
        codes = [code for code, _ in self.tc_commands]
        self.print_variables({"exit codes": codes})
        self.assertEqual(
            codes, [0] * len(codes), msg=self.parameters.MSG_ALEMBIC_SUCCEEDS, abort_on_fail=True
        )

    def bud_old_revision_has_no_session_table(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"revision": self.tc_before_revision, "table": self.tc_before_table})
        self.assertEqual(
            self.tc_before_revision,
            self.parameters.MIGRATION_BEFORE_CLI,
            msg=self.parameters.MSG_OLD_HEAD,
            abort_on_fail=False,
        )
        self.assertEqual(
            (self.tc_before_table,),
            (None,),
            msg=self.parameters.MSG_OLD_NO_TABLE,
            abort_on_fail=False,
        )

    def bud_upgrade_keeps_existing_rows(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"before": self.tc_before_rows, "upgraded": self.tc_upgraded_rows})
        self.assertEqual(
            self.tc_upgraded_rows,
            self.tc_before_rows,
            msg=self.parameters.MSG_UPGRADE_KEEPS_ROWS,
            abort_on_fail=False,
        )

    def bud_upgrade_reaches_the_single_head(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"heads": self.tc_heads, "revision": self.tc_upgraded_revision})
        self.assertEqual(
            len(self.tc_heads), 1, msg=self.parameters.MSG_SINGLE_HEAD, abort_on_fail=False
        )
        self.assertEqual(
            [self.tc_upgraded_revision],
            self.tc_heads,
            msg=self.parameters.MSG_AT_HEAD,
            abort_on_fail=False,
        )

    def bud_session_table_matches_the_model(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        table = self.tc_upgraded_table or {}
        self.print_variables({"table": table})
        self.assertEqual(
            table.get("columns"),
            self.bloom.bloom_cli_session_model_columns(),
            msg=self.parameters.MSG_TABLE_COLUMNS,
            abort_on_fail=False,
        )
        self.assertEqual(
            table.get("indexes"),
            self.parameters.CLI_SESSION_INDEXES,
            msg=self.parameters.MSG_TABLE_INDEXES,
            abort_on_fail=False,
        )
        self.assertEqual(
            table.get("cascade"),
            self.parameters.CLI_SESSION_CASCADE,
            msg=self.parameters.MSG_TABLE_CASCADE,
            abort_on_fail=False,
        )
        self.assertEqual(
            table.get("check"), 1, msg=self.parameters.MSG_TABLE_CHECK, abort_on_fail=False
        )
        self.assertEqual(
            table.get("sessions"), 0, msg=self.parameters.MSG_TABLE_EMPTY, abort_on_fail=False
        )

    def bud_sessions_are_stored(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"sessions": self.tc_stored_sessions})
        self.assertEqual(
            self.tc_stored_sessions,
            self.parameters.CLI_ADDED_SESSIONS,
            msg=self.parameters.MSG_SESSIONS_STORED,
            abort_on_fail=False,
        )

    def bud_downgrade_drops_the_table_and_keeps_rows(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables(
            {
                "revision": self.tc_downgraded_revision,
                "table": self.tc_downgraded_table,
                "rows": self.tc_downgraded_rows,
            }
        )
        self.assertEqual(
            self.tc_downgraded_revision,
            self.parameters.MIGRATION_BEFORE_CLI,
            msg=self.parameters.MSG_DOWNGRADE_REVISION,
            abort_on_fail=False,
        )
        self.assertEqual(
            (self.tc_downgraded_table,),
            (None,),
            msg=self.parameters.MSG_DOWNGRADE_DROPS,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.tc_downgraded_rows,
            self.tc_before_rows,
            msg=self.parameters.MSG_DOWNGRADE_KEEPS_ROWS,
            abort_on_fail=False,
        )

    def bud_upgrading_again_matches_the_first_upgrade(self):
        if not self.tc_postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        again = (self.tc_reupgraded_revision, self.tc_reupgraded_table, self.tc_reupgraded_rows)
        first = (self.tc_upgraded_revision, self.tc_upgraded_table, self.tc_before_rows)
        self.print_variables({"again": again, "first": first})
        self.assertEqual(again, first, msg=self.parameters.MSG_REUPGRADE_SAME, abort_on_fail=False)
