"""
* @file     ${tests/api/BLOOM_baseline_read_admission.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A baseline-read group gives no baseline reads until it is admitted to the project.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     This module tests a maintainer in a baseline-read group with no project admission.
"""

from tests.api.baseline_read_admission import BaselineReadAdmissionBase


class BaselineReadAdmissionTest(BaselineReadAdmissionBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        project = self.bloom.bloom_api_create_project(admin, self.parameters.ADMISSION_PREFIX)
        baseline = self.bloom.bloom_api_create_baseline(
            admin, project.json()["id"], self.parameters.BASELINE_NAME
        )
        user = self.bloom.bloom_api_create_user(
            admin,
            self.parameters.BASELINE_MEMBER_EMAIL,
            self.parameters.API_PASSWORD,
            self.parameters.API_MEMBER_ROLE,
        )
        member, _ = self.bloom.bloom_log_in(
            self.parameters.BASELINE_MEMBER_EMAIL, self.parameters.API_PASSWORD
        )
        policy = self.bloom.bloom_api_create_policy(
            admin, self.parameters.BASELINE_POLICY_NAME, self.parameters.BASELINE_PERMISSIONS
        )
        group = self.bloom.bloom_api_create_group(
            admin, self.parameters.BASELINE_GROUP_NAME, [policy.json()["id"]]
        )
        joined = self.bloom.bloom_api_add_group_member(admin, group.json()["id"], user.json()["id"])
        self.tc_reads = [
            answer.status_code
            for answer in self.bloom.bloom_api_read_baselines(
                member, project.json()["id"], baseline.json()["id"]
            )
        ]
        self.tc_setup = [
            (project.status_code, self.parameters.STATUS_CREATED),
            (baseline.status_code, self.parameters.STATUS_CREATED),
            (user.status_code, self.parameters.STATUS_CREATED),
            (policy.status_code, self.parameters.STATUS_CREATED),
            (group.status_code, self.parameters.STATUS_CREATED),
            (joined.status_code, self.parameters.STATUS_CREATED),
        ]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    BaselineReadAdmissionTest().run()
