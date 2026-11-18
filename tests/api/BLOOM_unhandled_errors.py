"""
* @file     ${tests/api/BLOOM_unhandled_errors.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An unhandled error is answered with a reference the user can report and without internal details.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests routes added to the application that raise an error, a conflict or a late commit failure.
"""

from tests.api.unhandled_errors import UnhandledErrorsBase


class UnhandledErrorsTest(UnhandledErrorsBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_plain_api()
        self.bloom.bloom_add_failing_routes()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    UnhandledErrorsTest().run()
