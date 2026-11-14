"""
* @file     ${tests/sec/BLOOM_no_database_ids_in_paths.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Only routes on the ticket-owned allowlist take a database id in their path.
* @author   Amine El Omari
* @date     2026-11-13
* @version  1.0.0
* @note     This module walks every API route and compares it with the allowlist.
"""

from tests.sec.no_database_ids_in_paths import NoDatabaseIdsInPathsBase


class NoDatabaseIdsInPathsTest(NoDatabaseIdsInPathsBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_integer_routes = {
            f"{method} {route.path}"
            for route in self.bloom.bloom_api_routes()
            if route.integer_path
            for method in route.method_list
        }
        self.tc_allowlisted = set().union(*self.parameters.DATABASE_ID_ROUTES.values())

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    NoDatabaseIdsInPathsTest().run()
