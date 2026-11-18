"""
* @file     ${tests/logic/BLOOM_reqif_limits.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    ReqIF uploads, archives and documents past a limit are refused, and parsing runs in a worker with a deadline.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the ReqIF request, archive and document limits with small hostile inputs.
"""

from tests.logic.reqif_limits import ReqifLimitsBase


class ReqifLimitsTest(ReqifLimitsBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ReqifLimitsTest().run()
