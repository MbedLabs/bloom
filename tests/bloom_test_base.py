"""
* @file     ${tests/bloom_test_base.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Shared Bloom test base: BudTestCase with BloomInterface and the parameters.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module provides the base class for Bloom test implementations.
"""

from budtestlibrary import BudTestCase

import tests.parameters as params
from tests.bloom_interface import BloomInterface


class BloomTestCase(BudTestCase):

    def setUpClass(self):
        self.bloom = BloomInterface()
        self.bloom.setUp()
        self.parameters = params
        self.log_info(f"BUDTEST_SEED={self.parameters.SEED}")

    def tearDownClass(self):
        self.bloom.tearDown()
