"""
* @file     ${tests/api/BLOOM_dashboard_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The dashboard reports totals per project, limited for an external reader to visible records of allowed types.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the dashboard on the full application as administrator and as an external reader.
"""

from tests.api.dashboard_http import DashboardHttpBase


class DashboardHttpTest(DashboardHttpBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DashboardHttpTest().run()
