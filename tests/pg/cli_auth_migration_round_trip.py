"""
* @file     ${tests/pg/cli_auth_migration_round_trip.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the CLI session migration up, down and up again on PostgreSQL.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of the CLI session migration round trip.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class CliAuthMigrationRoundTripBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_the_database_starts_before_the_cli_sessions(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        revision = self.bloom.bloom_read_revision()
        table = self.bloom.bloom_read_cli_session_table()
        self.print_variables({"prepared": self.prepared, "revision": revision, "table": table})
        self.assertEqual(
            self.prepared[0], 0, msg=self.parameters.MSG_ALEMBIC_SUCCEEDS, abort_on_fail=True
        )
        self.assertEqual(
            revision,
            self.parameters.MIGRATION_BEFORE_CLI,
            msg=self.parameters.MSG_OLD_HEAD,
            abort_on_fail=False,
        )
        self.assertEqual(
            (table,), (None,), msg=self.parameters.MSG_OLD_NO_TABLE, abort_on_fail=False
        )

    def bud_upgrade_keeps_existing_rows(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        rows = self.bloom.bloom_read_retained_rows(self.ids)
        self.print_variables({"exit code": code, "before": self.before_rows, "upgraded": rows})
        if code:
            self.log_info(output)
        self.assertEqual(code, 0, msg=self.parameters.MSG_ALEMBIC_SUCCEEDS, abort_on_fail=True)
        self.assertEqual(
            rows, self.before_rows, msg=self.parameters.MSG_UPGRADE_KEEPS_ROWS, abort_on_fail=False
        )

    def bud_upgrade_reaches_the_single_head(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        heads = self.bloom.bloom_list_alembic_heads()
        revision = self.bloom.bloom_read_revision()
        self.print_variables({"heads": heads, "revision": revision})
        self.assertEqual(len(heads), 1, msg=self.parameters.MSG_SINGLE_HEAD, abort_on_fail=False)
        self.assertEqual([revision], heads, msg=self.parameters.MSG_AT_HEAD, abort_on_fail=False)

    def bud_session_table_matches_the_model(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        table = self.bloom.bloom_read_cli_session_table() or {}
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
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.bloom.bloom_add_cli_sessions(self.ids["user"])
        sessions = self.bloom.bloom_read_cli_session_table()["sessions"]
        self.print_variables({"sessions": sessions})
        self.assertEqual(
            sessions,
            self.parameters.CLI_ADDED_SESSIONS,
            msg=self.parameters.MSG_SESSIONS_STORED,
            abort_on_fail=False,
        )

    def bud_downgrade_drops_the_table_and_keeps_rows(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.bloom.bloom_run_alembic(
            "downgrade", self.parameters.MIGRATION_BEFORE_CLI
        )
        revision = self.bloom.bloom_read_revision()
        table = self.bloom.bloom_read_cli_session_table()
        rows = self.bloom.bloom_read_retained_rows(self.ids)
        self.print_variables(
            {"exit code": code, "revision": revision, "table": table, "rows": rows}
        )
        if code:
            self.log_info(output)
        self.assertEqual(code, 0, msg=self.parameters.MSG_ALEMBIC_SUCCEEDS, abort_on_fail=True)
        self.assertEqual(
            revision,
            self.parameters.MIGRATION_BEFORE_CLI,
            msg=self.parameters.MSG_DOWNGRADE_REVISION,
            abort_on_fail=False,
        )
        self.assertEqual(
            (table,), (None,), msg=self.parameters.MSG_DOWNGRADE_DROPS, abort_on_fail=False
        )
        self.assertEqual(
            rows,
            self.before_rows,
            msg=self.parameters.MSG_DOWNGRADE_KEEPS_ROWS,
            abort_on_fail=False,
        )

    def bud_upgrading_again_matches_the_first_upgrade(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        heads = self.bloom.bloom_list_alembic_heads()
        revision = self.bloom.bloom_read_revision()
        table = self.bloom.bloom_read_cli_session_table() or {}
        rows = self.bloom.bloom_read_retained_rows(self.ids)
        self.print_variables(
            {"exit code": code, "revision": revision, "table": table, "rows": rows}
        )
        if code:
            self.log_info(output)
        self.assertEqual(code, 0, msg=self.parameters.MSG_ALEMBIC_SUCCEEDS, abort_on_fail=True)
        self.assertEqual(
            (
                [revision],
                table.get("columns"),
                table.get("indexes"),
                table.get("cascade"),
                table.get("check"),
                table.get("sessions"),
                rows,
            ),
            (
                heads,
                self.bloom.bloom_cli_session_model_columns(),
                self.parameters.CLI_SESSION_INDEXES,
                self.parameters.CLI_SESSION_CASCADE,
                1,
                0,
                self.before_rows,
            ),
            msg=self.parameters.MSG_REUPGRADE_SAME,
            abort_on_fail=False,
        )
