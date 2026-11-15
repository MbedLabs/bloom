"""
* @file     ${tests/api/BLOOM_baseline_read_owner.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    The admin and a project owner keep the baseline list and detail reads.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     This module tests the admin and a maintainer added as project owner with no policy.
"""

from tests.api.baseline_read_owner import BaselineReadOwnerBase


class BaselineReadOwnerTest(BaselineReadOwnerBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        project = self.bloom.bloom_api_create_project(admin, self.parameters.OWNED_PREFIX)
        baseline = self.bloom.bloom_api_create_baseline(
            admin, project.json()["id"], self.parameters.BASELINE_NAME
        )
        user = self.bloom.bloom_api_create_user(
            admin,
            self.parameters.BASELINE_MEMBER_EMAIL,
            self.parameters.API_PASSWORD,
            self.parameters.API_MEMBER_ROLE,
        )
        owner, _ = self.bloom.bloom_log_in(
            self.parameters.BASELINE_MEMBER_EMAIL, self.parameters.API_PASSWORD
        )
        made_owner = self.bloom.bloom_api_add_project_member(
            admin, project.json()["id"], user.json()["id"], [], owner=True
        )
        self.tc_baseline_id = baseline.json()["id"]
        self.tc_reads = {}
        for actor, headers in (("admin", admin), ("owner", owner)):
            listed, detail = self.bloom.bloom_api_read_baselines(
                headers, project.json()["id"], self.tc_baseline_id
            )
            self.tc_reads[actor] = (
                [listed.status_code, detail.status_code],
                self.tc_baseline_id in [item["id"] for item in listed.json()],
                detail.json().get("id"),
            )
        self.tc_setup = [
            (project.status_code, self.parameters.STATUS_CREATED),
            (baseline.status_code, self.parameters.STATUS_CREATED),
            (user.status_code, self.parameters.STATUS_CREATED),
            (made_owner.status_code, self.parameters.STATUS_CREATED),
        ]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    BaselineReadOwnerTest().run()
