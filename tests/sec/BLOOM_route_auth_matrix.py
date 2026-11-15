"""
* @file     ${tests/sec/BLOOM_route_auth_matrix.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Every API route outside the public and signed webhook lists needs a signed-in caller.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module walks every route the application registers under /api.
"""

from tests.sec.route_auth_matrix import RouteAuthMatrixBase


class RouteAuthMatrixTest(RouteAuthMatrixBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_routes = self.bloom.bloom_api_routes()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    RouteAuthMatrixTest().run()
