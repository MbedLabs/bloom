"""
* @file     ${tests/logic/BLOOM_alembic_baseline.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The migration chain stays a single explicit-DDL baseline with the deployed head id.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module reads the revision files of alembic/versions.
"""

from tests.logic.alembic_baseline import AlembicBaselineBase


class AlembicBaselineTest(AlembicBaselineBase):

    def setUpClass(self):
        super().setUpClass()
        pass

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AlembicBaselineTest().run()
