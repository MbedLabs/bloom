"""
* @file     ${tests/sec/route_auth_matrix.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that no Bloom API route is published without authentication.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the route authentication matrix.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class RouteAuthMatrixBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_every_private_route_has_an_authentication_boundary(self):
        exempt = self.parameters.ROUTE_PUBLIC_ENDPOINTS | self.parameters.ROUTE_SIGNED_WEBHOOKS
        unprotected = [
            f"{route.methods} {route.path} ({route.endpoint})"
            for route in self.tc_routes
            if route.endpoint not in exempt
            and route.dependencies.isdisjoint(self.parameters.ROUTE_AUTH_DEPENDENCIES)
        ]
        self.print_variables({"routes": len(self.tc_routes), "unprotected": unprotected})
        self.assertEqual(
            unprotected, [], msg=self.parameters.MSG_ROUTE_BOUNDARY, abort_on_fail=False
        )

    def bud_signed_webhook_allowlist_matches_the_routes(self):
        registered = {
            route.endpoint
            for route in self.tc_routes
            if route.endpoint in self.parameters.ROUTE_SIGNED_WEBHOOKS
        }
        self.print_variables({"registered": sorted(registered)})
        self.assertEqual(
            registered,
            self.parameters.ROUTE_SIGNED_WEBHOOKS,
            msg=self.parameters.MSG_ROUTE_WEBHOOKS,
            abort_on_fail=False,
        )
