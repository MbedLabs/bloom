"""
* @file     ${tests/logic/BLOOM_defect_managers.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    BLOOM-134: a user holds the Defect Managers group on a project and receives the email of a failed Jira send.
* @author   Amine El Omari
* @date     2026-11-18
* @version  1.0.0
* @note     This module tests an administrator, a Product Owner, a Defect Manager and a Tester on one project, and a Defect Manager of another project.
"""

from app.models.user import UserRole
from tests.logic.defect_managers import DefectManagersBase


class DefectManagersTest(DefectManagersBase):

    def setUpClass(self):
        super().setUpClass()
        p, bloom = self.parameters, self.bloom
        bloom.bloom_seed_default_catalogue()
        self.project_id = bloom.bloom_create_project(p.DM_PROJECT)
        other_project = bloom.bloom_create_project(p.DM_OTHER_PROJECT)
        bloom.bloom_add_user(p.DM_ADMIN, UserRole.admin)
        for email, group, project in (
            (p.DM_OWNER, p.DM_OWNERS_GROUP, self.project_id),
            (p.DM_MANAGER, p.DM_GROUP, self.project_id),
            (p.DM_TESTER, p.DM_TESTERS_GROUP, self.project_id),
            (p.DM_OTHER_MANAGER, p.DM_GROUP, other_project),
        ):
            user_id = bloom.bloom_add_user(email, UserRole.maintainer)
            bloom.bloom_give_project_group(user_id, project, group)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    DefectManagersTest().run()
