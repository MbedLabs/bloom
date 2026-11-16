"""
* @file     ${tests/api/BLOOM_http_api.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The probes, root and docs switch answer as deployed; signing in opens the API.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests the full app in-process with an admin account.
"""

from tests.api.http_api import HttpApiBase


class HttpApiTest(HttpApiBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        call = self.bloom.bloom_api_call
        self.health = call("GET", self.parameters.HTTP_HEALTH)
        self.root = call("GET", self.parameters.HTTP_ROOT)
        self.ready = call("GET", self.parameters.HTTP_READY)
        self.openapi = call("GET", self.parameters.HTTP_OPENAPI).status
        self.wrong_password = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.HTTP_WRONG_PASSWORD
        )[1]
        self.anonymous_projects = call("GET", self.parameters.HTTP_PROJECTS).status
        self.anonymous_links = call(
            "GET",
            self.parameters.HTTP_LINKS,
            params={"project_id": self.parameters.HTTP_SOME_PROJECT},
        ).status
        admin, self.login = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        self.me = call("GET", self.parameters.HTTP_ME, headers=admin)
        self.projects = call("GET", self.parameters.HTTP_PROJECTS, headers=admin)
        self.links = call(
            "GET",
            self.parameters.HTTP_LINKS,
            headers=admin,
            params={"project_id": self.parameters.HTTP_MISSING_PROJECT},
        ).status

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    HttpApiTest().run()
