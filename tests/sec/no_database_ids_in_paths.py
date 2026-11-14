"""
* @file     ${tests/sec/no_database_ids_in_paths.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that API routes take database ids only where a ticket owns them.
* @author   Amine El Omari
* @date     2026-11-13
* @version  1.0.0
* @note     Base class containing the bud methods of the database id route gate.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class NoDatabaseIdsInPathsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_no_unlisted_route_takes_a_database_id(self):
        unlisted = sorted(self.tc_integer_routes - self.tc_allowlisted)
        self.print_variables({"integer routes": len(self.tc_integer_routes), "unlisted": unlisted})
        self.assertEqual(
            unlisted, [], msg=self.parameters.MSG_DATABASE_ID_UNLISTED, abort_on_fail=False
        )

    def bud_every_allowlisted_route_still_takes_a_database_id(self):
        stale = sorted(self.tc_allowlisted - self.tc_integer_routes)
        self.print_variables({"allowlisted": len(self.tc_allowlisted), "stale": stale})
        self.assertEqual(stale, [], msg=self.parameters.MSG_DATABASE_ID_STALE, abort_on_fail=False)

    def bud_each_route_has_one_owner(self):
        seen = {}
        shared = []
        for owner, routes in self.parameters.DATABASE_ID_ROUTES.items():
            for route in routes:
                if route in seen:
                    shared.append(f"{route} ({seen[route]}, {owner})")
                seen[route] = owner
        self.print_variables({"shared": shared})
        self.assertEqual(
            shared, [], msg=self.parameters.MSG_DATABASE_ID_ONE_OWNER, abort_on_fail=False
        )

    def bud_suite_and_campaign_routes_take_no_database_id(self):
        owned = sorted(
            route
            for route in self.tc_integer_routes | self.tc_allowlisted
            if route.split(" ", 1)[1].startswith(self.parameters.DATABASE_ID_FREE_PREFIXES)
        )
        self.print_variables({"owned": owned})
        self.assertEqual(owned, [], msg=self.parameters.MSG_DATABASE_ID_SUITES, abort_on_fail=False)
