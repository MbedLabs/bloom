"""
* @file     ${tests/logic/BLOOM_tc_steps.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Step rows have one text form that every export writes and every import reads back.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the step functions and the XML and Markdown round trips.
"""

from tests.logic.tc_steps import TcStepsBase


class TcStepsTest(TcStepsBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    TcStepsTest().run()
