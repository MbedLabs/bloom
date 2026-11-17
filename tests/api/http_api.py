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
        health = self.bloom.bloom_api_call("GET", self.parameters.HTTP_HEALTH)
        body = health.body or {}
        self.print_variables({"status": health.status, "body": body})
        self._equal(health.status, self.parameters.STATUS_OK, self.parameters.MSG_HTTP_HEALTH_OK)
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
        root = self.bloom.bloom_api_call("GET", self.parameters.HTTP_ROOT)
        body = root.body or {}
        self.print_variables({"status": root.status, "body": body})
        self._equal(root.status, self.parameters.STATUS_OK, self.parameters.MSG_HTTP_ROOT_OK)
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
        ready = self.bloom.bloom_api_call("GET", self.parameters.HTTP_READY)
        body = ready.body or {}
        self.print_variables({"status": ready.status, "body": body})
        self._equal(ready.status, self.parameters.STATUS_OK, self.parameters.MSG_HTTP_READY_OK)
        self._equal(
            body.get("status"), self.parameters.HTTP_READY_STATUS, self.parameters.MSG_HTTP_READY
        )
        self._equal(
            body.get("database"), self.parameters.HTTP_CONNECTED, self.parameters.MSG_HTTP_READY_DB
        )

    def bud_openapi_is_hidden_while_docs_are_off(self):
        openapi = self.bloom.bloom_api_call("GET", self.parameters.HTTP_OPENAPI).status
        self.print_variables({"status": openapi})
        self._equal(
            openapi,
            self.parameters.STATUS_NOT_FOUND,
            self.parameters.MSG_HTTP_OPENAPI_HIDDEN,
        )

    def bud_wrong_password_is_refused(self):
        wrong_password = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.HTTP_WRONG_PASSWORD
        )[1]
        self.print_variables({"status": wrong_password})
        self._equal(
            wrong_password,
            self.parameters.STATUS_UNAUTHORIZED,
            self.parameters.MSG_HTTP_WRONG_PASSWORD,
        )

    def bud_projects_and_links_need_a_signed_in_user(self):
        anonymous_projects = self.bloom.bloom_api_call("GET", self.parameters.HTTP_PROJECTS).status
        anonymous_links = self.bloom.bloom_api_call(
            "GET",
            self.parameters.HTTP_LINKS,
            params={"project_id": self.parameters.HTTP_SOME_PROJECT},
        ).status
        self.print_variables({"projects": anonymous_projects, "links": anonymous_links})
        self._equal(
            anonymous_projects,
            self.parameters.STATUS_UNAUTHORIZED,
            self.parameters.MSG_HTTP_PROJECTS_AUTH,
        )
        self._equal(
            anonymous_links,
            self.parameters.STATUS_UNAUTHORIZED,
            self.parameters.MSG_HTTP_LINKS_AUTH,
        )

    def bud_signed_in_admin_reads_account_projects_and_links(self):
        admin, login = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        account = self.bloom.bloom_api_call("GET", self.parameters.HTTP_ME, headers=admin)
        projects = self.bloom.bloom_api_call("GET", self.parameters.HTTP_PROJECTS, headers=admin)
        links = self.bloom.bloom_api_call(
            "GET",
            self.parameters.HTTP_LINKS,
            headers=admin,
            params={"project_id": self.parameters.HTTP_MISSING_PROJECT},
        ).status
        me = account.body or {}
        self.print_variables(
            {
                "login": login,
                "me": account.status,
                "email": me.get("email"),
                "projects": projects.status,
                "links": links,
            }
        )
        self._equal(login, self.parameters.STATUS_OK, self.parameters.MSG_HTTP_LOGIN)
        self._equal(account.status, self.parameters.STATUS_OK, self.parameters.MSG_HTTP_ME)
        self._equal(
            me.get("email"), self.parameters.API_ADMIN_EMAIL, self.parameters.MSG_HTTP_ME_EMAIL
        )
        self._equal(projects.status, self.parameters.STATUS_OK, self.parameters.MSG_HTTP_PROJECTS)
        self.assertTrue(
            isinstance(projects.body, list),
            msg=self.parameters.MSG_HTTP_PROJECTS_LIST,
            expected="a list",
            actual=type(projects.body).__name__,
            abort_on_fail=False,
        )
        self._equal(links, self.parameters.STATUS_NOT_FOUND, self.parameters.MSG_HTTP_LINKS_MISSING)

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
