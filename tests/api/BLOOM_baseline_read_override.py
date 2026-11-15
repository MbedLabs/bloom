"""
* @file     ${tests/api/BLOOM_baseline_read_override.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An explicit project override decides both baseline reads, the group's policy unchanged.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     This module tests a maintainer in a baseline-read group, then under a project override.
"""

from tests.api.baseline_read_override import BaselineReadOverrideBase


class BaselineReadOverrideTest(BaselineReadOverrideBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        project = self.bloom.bloom_api_create_project(admin, self.parameters.SCOPED_PREFIX)
        other = self.bloom.bloom_api_create_project(admin, self.parameters.SEPARATE_PREFIX)
        baseline = self.bloom.bloom_api_create_baseline(
            admin, project.json()["id"], self.parameters.BASELINE_NAME
        )
        other_baseline = self.bloom.bloom_api_create_baseline(
            admin, other.json()["id"], self.parameters.BASELINE_NAME
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
        baseline_read = self.bloom.bloom_api_create_policy(
            admin, self.parameters.BASELINE_POLICY_NAME, self.parameters.BASELINE_PERMISSIONS
        )
        group = self.bloom.bloom_api_create_group(
            admin, self.parameters.BASELINE_GROUP_NAME, [baseline_read.json()["id"]]
        )
        joined = self.bloom.bloom_api_add_group_member(admin, group.json()["id"], user.json()["id"])
        admitted = self.bloom.bloom_api_admit_group(admin, group.json()["id"], project.json()["id"])
        self.tc_project_id = project.json()["id"]
        self.tc_baseline_id = baseline.json()["id"]
        self.tc_baseline_policy_id = baseline_read.json()["id"]
        self.tc_admitted = [
            answer.status_code
            for answer in self.bloom.bloom_api_read_baselines(
                member, self.tc_project_id, self.tc_baseline_id
            )
        ]

        requirements_read = self.bloom.bloom_api_create_policy(
            admin,
            self.parameters.REQUIREMENT_POLICY_NAME,
            self.parameters.REQUIREMENT_PERMISSIONS,
            self.parameters.REQUIREMENT_TYPES,
        )
        replacement = self.bloom.bloom_api_add_project_member(
            admin, self.tc_project_id, user.json()["id"], [requirements_read.json()["id"]]
        )
        self.tc_overridden = [
            answer.status_code
            for answer in self.bloom.bloom_api_read_baselines(
                member, self.tc_project_id, self.tc_baseline_id
            )
        ]

        allowed = self.bloom.bloom_api_update_project_member(
            admin,
            self.tc_project_id,
            replacement.json()["id"],
            [requirements_read.json()["id"], self.tc_baseline_policy_id],
        )
        listed, detail = self.bloom.bloom_api_read_baselines(
            member, self.tc_project_id, self.tc_baseline_id
        )
        self.tc_allowed = (
            [listed.status_code, detail.status_code],
            self.tc_baseline_id in [item["id"] for item in listed.json()],
            detail.json().get("id"),
        )
        self.tc_other = [
            answer.status_code
            for answer in self.bloom.bloom_api_read_baselines(
                member, other.json()["id"], other_baseline.json()["id"]
            )
        ]
        self.tc_group_policies = self.bloom.bloom_api_get_group(admin, group.json()["id"]).json()[
            "policy_ids"
        ]
        self.tc_setup = [
            (project.status_code, self.parameters.STATUS_CREATED),
            (other.status_code, self.parameters.STATUS_CREATED),
            (baseline.status_code, self.parameters.STATUS_CREATED),
            (other_baseline.status_code, self.parameters.STATUS_CREATED),
            (user.status_code, self.parameters.STATUS_CREATED),
            (baseline_read.status_code, self.parameters.STATUS_CREATED),
            (group.status_code, self.parameters.STATUS_CREATED),
            (joined.status_code, self.parameters.STATUS_CREATED),
            (admitted.status_code, self.parameters.STATUS_CREATED),
            (requirements_read.status_code, self.parameters.STATUS_CREATED),
            (replacement.status_code, self.parameters.STATUS_CREATED),
            (allowed.status_code, self.parameters.STATUS_OK),
        ]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    BaselineReadOverrideTest().run()
