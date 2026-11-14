"""
* @file     ${tests/api/BLOOM_baseline_snapshot_reader.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A reader sees the baseline records they may read now and only counts for the rest.
* @author   Amine El Omari
* @date     2026-11-07
* @version  1.0.0
* @note     This module tests a baseline of one requirement and one SPEC document and its reader.
"""

from tests.api.baseline_snapshot_reader import BaselineSnapshotReaderBase


class BaselineSnapshotReaderTest(BaselineSnapshotReaderBase):

    def setUpClass(self):
        super().setUpClass()
        self.bloom.bloom_start_full_api()
        self.bloom.bloom_add_admin(self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD)
        admin, _ = self.bloom.bloom_log_in(
            self.parameters.API_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        project = self.bloom.bloom_api_create_project(admin, self.parameters.SNAPSHOT_PREFIX)
        project_id = project.json()["id"]
        requirement = self.bloom.bloom_api_create_artefact(
            admin,
            self.parameters.REQUIREMENT_KIND,
            project_id,
            self.parameters.SNAPSHOT_REQUIREMENT_TITLE,
        )
        document = self.bloom.bloom_api_create_artefact(
            admin,
            self.parameters.DOCUMENT_KIND,
            project_id,
            self.parameters.SNAPSHOT_DOCUMENT_TITLE,
        )
        baseline = self.bloom.bloom_api_create_baseline(
            admin, project_id, self.parameters.BASELINE_NAME
        )
        policy = self.bloom.bloom_api_create_policy_rules(
            admin, self.parameters.BASELINE_POLICY_NAME, self.parameters.SNAPSHOT_READER_RULES
        )
        group = self.bloom.bloom_api_create_group(
            admin, self.parameters.BASELINE_GROUP_NAME, [policy.json()["id"]]
        )
        admitted = self.bloom.bloom_api_admit_group(admin, group.json()["id"], project_id)
        user = self.bloom.bloom_api_create_user(
            admin,
            self.parameters.SNAPSHOT_READER_EMAIL,
            self.parameters.API_PASSWORD,
            self.parameters.API_MEMBER_ROLE,
        )
        joined = self.bloom.bloom_api_add_group_member(admin, group.json()["id"], user.json()["id"])
        reader, _ = self.bloom.bloom_log_in(
            self.parameters.SNAPSHOT_READER_EMAIL, self.parameters.API_PASSWORD
        )
        self.tc_requirement = requirement.json()
        self.tc_baseline_id = baseline.json()["id"]
        self.tc_listed, self.tc_detail = self.bloom.bloom_api_read_baselines(
            reader, project_id, self.tc_baseline_id
        )
        self.tc_setup = [
            (project.status_code, self.parameters.STATUS_CREATED),
            (requirement.status_code, self.parameters.STATUS_CREATED),
            (document.status_code, self.parameters.STATUS_CREATED),
            (baseline.status_code, self.parameters.STATUS_CREATED),
            (policy.status_code, self.parameters.STATUS_CREATED),
            (group.status_code, self.parameters.STATUS_CREATED),
            (admitted.status_code, self.parameters.STATUS_CREATED),
            (user.status_code, self.parameters.STATUS_CREATED),
            (joined.status_code, self.parameters.STATUS_CREATED),
        ]

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    BaselineSnapshotReaderTest().run()
