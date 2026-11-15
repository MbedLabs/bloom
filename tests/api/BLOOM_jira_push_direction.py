"""
* @file     ${tests/api/BLOOM_jira_push_direction.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    Edits reach Jira only when the direction includes Bloom to Jira.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     This module tests edits of a linked defect and change request under two directions.
"""

from tests.api.jira_push_direction import JiraPushDirectionBase


class JiraPushDirectionTest(JiraPushDirectionBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_env = self.bloom.bloom_create_webhook_environment()
        self.tc_pushed = self.bloom.bloom_record_pushes()
        self.bloom.bloom_push_edits(
            self.tc_env.defect_id, self.tc_env.change_id, {"title": self.parameters.CHANGED_TITLE}
        )
        self.tc_before = list(self.tc_pushed)
        self.bloom.bloom_update_setting(
            self.tc_env.setting_id, direction=self.parameters.DIRECTION_BOTH
        )
        self.bloom.bloom_push_edits(
            self.tc_env.defect_id, self.tc_env.change_id, {"title": self.parameters.CHANGED_TITLE}
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    JiraPushDirectionTest().run()
