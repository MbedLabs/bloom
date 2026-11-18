"""
* @file     ${tests/api/BLOOM_report_requests.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A reader who sees a source and its run requests a report; Bud reads the mailbox, refuses or delivers.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the report request routes on the full application; each case starts from a new database.
"""

from tests.api.report_requests import ReportRequestsBase


class ReportRequestsTest(ReportRequestsBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_report_request_api()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ReportRequestsTest().run()
