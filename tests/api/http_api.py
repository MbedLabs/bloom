"""
* @file     ${tests/api/http_api.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the probes, the root, the docs switch and signing in over HTTP.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the basic HTTP checks.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class HttpApiBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_health_answers_without_the_database(self):
        body = self.health.body or {}
        self.print_variables({"status": self.health.status, "body": body})
        self._equal(
            self.health.status, self.parameters.STATUS_OK, self.parameters.MSG_HTTP_HEALTH_OK
        )
        self._equal(
            body.get("status"), self.parameters.HTTP_HEALTHY, self.parameters.MSG_HTTP_HEALTHY
        )
        self.assertIn(
            self.parameters.HTTP_VERSION_KEY,
            body,
            msg=self.parameters.MSG_HTTP_HEALTH_VERSION,
            abort_on_fail=False,
        )
        self.assertNotEqual(
            body.get("database"),
            self.parameters.HTTP_CONNECTED,
            msg=self.parameters.MSG_HTTP_HEALTH_NO_DB,
            abort_on_fail=False,
        )

    def bud_root_names_the_product(self):
        body = self.root.body or {}
        self.print_variables({"status": self.root.status, "body": body})
        self._equal(self.root.status, self.parameters.STATUS_OK, self.parameters.MSG_HTTP_ROOT_OK)
        self._equal(
            body.get("message"), self.parameters.HTTP_PRODUCT, self.parameters.MSG_HTTP_ROOT_PRODUCT
        )
        self.assertIn(
            self.parameters.HTTP_VERSION_KEY,
            body,
            msg=self.parameters.MSG_HTTP_ROOT_VERSION,
            abort_on_fail=False,
        )

    def bud_ready_confirms_the_database(self):
        body = self.ready.body or {}
        self.print_variables({"status": self.ready.status, "body": body})
        self._equal(self.ready.status, self.parameters.STATUS_OK, self.parameters.MSG_HTTP_READY_OK)
        self._equal(
            body.get("status"), self.parameters.HTTP_READY_STATUS, self.parameters.MSG_HTTP_READY
        )
        self._equal(
            body.get("database"), self.parameters.HTTP_CONNECTED, self.parameters.MSG_HTTP_READY_DB
        )

    def bud_openapi_is_hidden_while_docs_are_off(self):
        self.print_variables({"status": self.openapi})
        self._equal(
            self.openapi,
            self.parameters.STATUS_NOT_FOUND,
            self.parameters.MSG_HTTP_OPENAPI_HIDDEN,
        )

    def bud_wrong_password_is_refused(self):
        self.print_variables({"status": self.wrong_password})
        self._equal(
            self.wrong_password,
            self.parameters.STATUS_UNAUTHORIZED,
            self.parameters.MSG_HTTP_WRONG_PASSWORD,
        )

    def bud_projects_and_links_need_a_signed_in_user(self):
        self.print_variables({"projects": self.anonymous_projects, "links": self.anonymous_links})
        self._equal(
            self.anonymous_projects,
            self.parameters.STATUS_UNAUTHORIZED,
            self.parameters.MSG_HTTP_PROJECTS_AUTH,
        )
        self._equal(
            self.anonymous_links,
            self.parameters.STATUS_UNAUTHORIZED,
            self.parameters.MSG_HTTP_LINKS_AUTH,
        )

    def bud_signed_in_admin_reads_account_projects_and_links(self):
        me = self.me.body or {}
        self.print_variables(
            {
                "login": self.login,
                "me": self.me.status,
                "email": me.get("email"),
                "projects": self.projects.status,
                "links": self.links,
            }
        )
        self._equal(self.login, self.parameters.STATUS_OK, self.parameters.MSG_HTTP_LOGIN)
        self._equal(self.me.status, self.parameters.STATUS_OK, self.parameters.MSG_HTTP_ME)
        self._equal(
            me.get("email"), self.parameters.API_ADMIN_EMAIL, self.parameters.MSG_HTTP_ME_EMAIL
        )
        self._equal(
            self.projects.status, self.parameters.STATUS_OK, self.parameters.MSG_HTTP_PROJECTS
        )
        self.assertTrue(
            isinstance(self.projects.body, list),
            msg=self.parameters.MSG_HTTP_PROJECTS_LIST,
            expected="a list",
            actual=type(self.projects.body).__name__,
            abort_on_fail=False,
        )
        self._equal(
            self.links, self.parameters.STATUS_NOT_FOUND, self.parameters.MSG_HTTP_LINKS_MISSING
        )

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
