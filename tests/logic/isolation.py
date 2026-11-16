"""
* @file     ${tests/logic/isolation.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that loading the test configuration isolates credentials, mail and the database.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the test isolation.
"""

import json

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class IsolationBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_inherited_credentials_are_replaced(self):
        values = self.parameters
        run = self.bloom.bloom_run_test_bootstrap(values.ISO_READ_CREDENTIALS)
        observed = json.loads(run.output)
        self.assertEqual(
            observed["dotenv"], "1", msg=values.MSG_ISO_DOTENV_OFF, abort_on_fail=False
        )
        for prefix in ("", "BLOOM_"):
            for name, expected in values.ISO_REPLACED.items():
                self.assertEqual(
                    observed[prefix + name],
                    expected,
                    msg=values.MSG_ISO_REPLACED.format(name=prefix + name),
                    abort_on_fail=False,
                )

    def bud_external_smtp_is_blocked_before_the_network(self):
        run = self.bloom.bloom_run_test_bootstrap(self.parameters.ISO_EXTERNAL_SMTP)
        self.print_variables({"output": run.output, "errors": run.errors[-300:]})
        self.assertEqual(
            (run.failed, run.output),
            (False, "blocked before network"),
            msg=self.parameters.MSG_ISO_EXTERNAL_SMTP,
            abort_on_fail=False,
        )

    def bud_smtp_authentication_is_blocked_before_credentials(self):
        run = self.bloom.bloom_run_test_bootstrap(self.parameters.ISO_SMTP_AUTH)
        self.print_variables({"output": run.output, "errors": run.errors[-300:]})
        self.assertEqual(
            (run.failed, run.output),
            (False, "blocked before credentials"),
            msg=self.parameters.MSG_ISO_SMTP_AUTH,
            abort_on_fail=False,
        )

    def bud_the_test_mailpit_is_allowed(self):
        run = self.bloom.bloom_run_test_bootstrap(self.parameters.ISO_MAILPIT)
        self.print_variables({"output": run.output, "errors": run.errors[-300:]})
        self.assertEqual(
            (run.failed, run.output),
            (False, "allowed"),
            msg=self.parameters.MSG_ISO_MAILPIT,
            abort_on_fail=False,
        )

    def bud_a_live_database_is_refused_without_showing_its_address(self):
        values = self.parameters
        run = self.bloom.bloom_run_test_bootstrap(
            extra_env={"DATABASE_URL": values.ISO_LIVE_DATABASE}
        )
        self.print_variables({"errors": run.errors[-300:]})
        self.assertEqual(
            (
                run.failed,
                values.ISO_DATABASE_REFUSAL in run.errors,
                "synthetic-password" in run.errors,
                "db.example.com" in run.errors,
            ),
            (True, True, False, False),
            msg=values.MSG_ISO_LIVE_DATABASE,
            abort_on_fail=False,
        )

    def bud_operator_dotenv_reads_are_blocked(self):
        run = self.bloom.bloom_run_test_bootstrap(self.parameters.ISO_DOTENV_READ)
        self.print_variables({"output": run.output, "errors": run.errors[-300:]})
        self.assertEqual(
            (run.failed, run.output),
            (False, "operator dotenv blocked"),
            msg=self.parameters.MSG_ISO_DOTENV_READ,
            abort_on_fail=False,
        )

    def bud_database_connection_overrides_are_refused(self):
        for suffix in self.parameters.ISO_OVERRIDES:
            run = self.bloom.bloom_run_test_bootstrap(
                extra_env={"DATABASE_URL": self.parameters.ISO_TEST_DATABASE + suffix}
            )
            self.assertTrue(
                run.failed,
                msg=self.parameters.MSG_ISO_OVERRIDE.format(suffix=suffix),
                abort_on_fail=False,
            )

    def bud_ambient_aws_credentials_are_replaced(self):
        run = self.bloom.bloom_run_test_bootstrap(
            self.parameters.ISO_AWS_READ, self.parameters.ISO_AWS_INHERITED
        )
        self.print_variables({"output": run.output})
        self.assertEqual(
            json.loads(run.output),
            self.parameters.ISO_AWS_REPLACED,
            msg=self.parameters.MSG_ISO_AWS,
            abort_on_fail=False,
        )

    def bud_the_settings_do_not_open_a_dotenv_file(self):
        run = self.bloom.bloom_run_test_bootstrap(
            self.parameters.ISO_SETTINGS_DOTENV, with_folder=True
        )
        self.print_variables({"output": run.output, "errors": run.errors[-300:]})
        self.assertEqual(
            (run.failed, run.output),
            (False, "dotenv source not opened"),
            msg=self.parameters.MSG_ISO_SETTINGS,
            abort_on_fail=False,
        )

    def bud_the_rate_limiter_loads_without_the_dotenv_file(self):
        run = self.bloom.bloom_run_test_bootstrap(self.parameters.ISO_LIMITER)
        self.print_variables({"output": run.output, "errors": run.errors[-300:]})
        self.assertEqual(
            (run.failed, run.output),
            (False, "limiter loaded safely"),
            msg=self.parameters.MSG_ISO_LIMITER,
            abort_on_fail=False,
        )

    def bud_other_database_paths_and_drivers_are_refused(self):
        for what, address in self.parameters.ISO_WRONG_DATABASES:
            run = self.bloom.bloom_run_test_bootstrap(extra_env={"DATABASE_URL": address})
            self.assertTrue(
                run.failed,
                msg=self.parameters.MSG_ISO_WRONG_DATABASE.format(what=what),
                abort_on_fail=False,
            )

    def bud_a_temporary_migration_database_is_allowed(self):
        run = self.bloom.bloom_run_test_bootstrap(
            "print('accepted')", {"DATABASE_URL": self.parameters.ISO_MIGRATION_DATABASE}
        )
        self.assertEqual(
            (run.failed, run.output),
            (False, "accepted"),
            msg=self.parameters.MSG_ISO_MIGRATION_DATABASE,
            abort_on_fail=False,
        )

    def bud_a_temporary_database_allows_no_overrides(self):
        address = self.parameters.ISO_MIGRATION_DATABASE + self.parameters.ISO_OVERRIDES[0]
        run = self.bloom.bloom_run_test_bootstrap(extra_env={"DATABASE_URL": address})
        self.assertTrue(
            run.failed, msg=self.parameters.MSG_ISO_MIGRATION_OVERRIDE, abort_on_fail=False
        )

    def bud_local_development_postgres_ports_are_refused(self):
        values = self.parameters
        for port in values.ISO_DEV_POSTGRES_PORTS:
            address = values.ISO_TEST_DATABASE.replace(":15432", port)
            run = self.bloom.bloom_run_test_bootstrap(extra_env={"DATABASE_URL": address})
            self.assertEqual(
                (run.failed, values.ISO_DATABASE_REFUSAL in run.errors),
                (True, True),
                msg=values.MSG_ISO_DEV_POSTGRES.format(port=port),
                abort_on_fail=False,
            )

    def bud_another_postgres_port_is_allowed(self):
        run = self.bloom.bloom_run_test_bootstrap(
            extra_env={"DATABASE_URL": self.parameters.ISO_OTHER_PORT_DATABASE}
        )
        self.assertEqual(
            run.failed, False, msg=self.parameters.MSG_ISO_OTHER_POSTGRES, abort_on_fail=False
        )

    def bud_default_services_use_the_dedicated_ports(self):
        run = self.bloom.bloom_run_test_bootstrap(
            self.parameters.ISO_READ_SERVICES, {"DATABASE_URL": ""}
        )
        self.print_variables({"output": run.output})
        self.assertEqual(
            json.loads(run.output),
            self.parameters.ISO_DEFAULT_SERVICES,
            msg=self.parameters.MSG_ISO_DEFAULTS,
            abort_on_fail=False,
        )

    def bud_local_development_mail_ports_are_refused(self):
        values = self.parameters
        for port in values.ISO_DEV_SMTP_PORTS:
            run = self.bloom.bloom_run_test_bootstrap(extra_env={"TEST_SMTP_PORT": port})
            self.assertEqual(
                (run.failed, values.ISO_SMTP_REFUSAL in run.errors),
                (True, True),
                msg=values.MSG_ISO_DEV_SMTP.format(port=port),
                abort_on_fail=False,
            )

    def bud_another_mail_port_is_allowed(self):
        run = self.bloom.bloom_run_test_bootstrap(
            self.parameters.ISO_OTHER_MAILPIT, {"TEST_SMTP_PORT": "21025"}
        )
        self.assertEqual(
            (run.failed, run.output),
            (False, "allowed"),
            msg=self.parameters.MSG_ISO_OTHER_SMTP,
            abort_on_fail=False,
        )

    def bud_connections_to_the_development_mailpit_are_blocked(self):
        for port in self.parameters.ISO_DEV_MAILPIT_PORTS:
            run = self.bloom.bloom_run_test_bootstrap(
                self.parameters.ISO_CONNECT_MAILPIT.format(port=port)
            )
            self.assertEqual(
                (run.failed, run.output),
                (False, "blocked before network"),
                msg=self.parameters.MSG_ISO_DEV_MAILPIT.format(port=port),
                abort_on_fail=False,
            )
