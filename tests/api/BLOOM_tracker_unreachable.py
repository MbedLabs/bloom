"""
* @file     ${tests/api/BLOOM_tracker_unreachable.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An unreachable issue tracker is answered as a gateway error naming the tracker.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests refreshing a defect from GitHub on the full application while the tracker call fails.
"""

from tests.api.tracker_unreachable import TrackerUnreachableBase


class TrackerUnreachableTest(TrackerUnreachableBase):

    def setUpClass(self):
        super().setUpClass()
        self.admin = self.bloom.bloom_start_api_with_admin()

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TrackerUnreachableTest().run()
