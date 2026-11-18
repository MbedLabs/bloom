"""
* @file     ${tests/api/public_id_paths.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that suites and campaigns are addressed by their public id.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the public id addresses.
"""

import re

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class PublicIdPathsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_suite_is_addressed_by_its_public_id_only(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PID_PREFIXES[0])
        suite = self.bloom.bloom_api_add_suite(self.admin, project["id"], "Demo", [])
        public, by_number = (
            f"/api/test-suites/{suite['suite_id']}",
            f"/api/test-suites/{suite['id']}",
        )
        self.assertEqual(
            (
                bool(re.fullmatch(rf"{project['prefix']}-TS-\d{{3,}}", suite["suite_id"])),
                self.bloom.bloom_api_call("GET", public, self.admin).body["id"],
            ),
            (True, suite["id"]),
            msg=values.MSG_PID_SUITE_ID,
            abort_on_fail=False,
            method="GET",
            endpoint=public,
        )
        for method, body in (("GET", None), ("PATCH", {"name": "Renamed"}), ("DELETE", None)):
            answer = self.bloom.bloom_api_call(method, by_number, self.admin, json=body)
            self.assertEqual(
                (answer.status, answer.body["detail"]),
                (values.STATUS_NOT_FOUND, "Test suite not found"),
                msg=values.MSG_PID_SUITE_NUMBER.format(method=method),
                abort_on_fail=False,
                method=method,
                endpoint=by_number,
            )
        renamed = self.bloom.bloom_api_call("PATCH", public, self.admin, json={"name": "Renamed"})
        deleted = self.bloom.bloom_api_call("DELETE", public, self.admin)
        self.assertEqual(
            (
                renamed.status,
                renamed.body["name"],
                deleted.status,
                self.bloom.bloom_api_call("GET", public, self.admin).status,
            ),
            (values.STATUS_OK, "Renamed", values.STATUS_NO_CONTENT, values.STATUS_NOT_FOUND),
            msg=values.MSG_PID_SUITE_CHANGED,
            abort_on_fail=False,
            method="PATCH",
            endpoint=public,
        )

    def bud_suite_items_use_the_test_case_public_id(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PID_PREFIXES[1])
        case = self.bloom.bloom_api_add_test_case(self.admin, project["id"], "Case").body
        suite = self.bloom.bloom_api_add_suite(self.admin, project["id"], "Demo", [])
        items = f"/api/test-suites/{suite['suite_id']}/items"
        numbered = self.bloom.bloom_api_call(
            "POST", items, self.admin, params={"test_case_id": case["id"]}
        )
        self.assertEqual(
            numbered.status,
            values.STATUS_NOT_FOUND,
            msg=values.MSG_PID_ITEM_NUMBER,
            abort_on_fail=False,
            method="POST",
            endpoint=items,
        )
        added = self.bloom.bloom_api_call(
            "POST", items, self.admin, params={"test_case_id": case["tc_id"]}
        )
        again = self.bloom.bloom_api_call(
            "POST", items, self.admin, params={"test_case_id": case["tc_id"]}
        )
        self.assertEqual(
            (added.status, added.body["suite_id"], added.body["test_case_id"], again.status),
            (values.STATUS_CREATED, suite["id"], case["id"], values.STATUS_BAD_REQUEST),
            msg=values.MSG_PID_ITEM_ADDED,
            abort_on_fail=False,
            method="POST",
            endpoint=items,
        )
        removed = [
            self.bloom.bloom_api_call("DELETE", f"{items}/{added.body['id']}", self.admin).status,
            self.bloom.bloom_api_call("DELETE", f"{items}/{case['tc_id']}", self.admin).status,
            self.bloom.bloom_api_call(
                "GET", f"/api/test-suites/{suite['suite_id']}", self.admin
            ).body["items"],
            self.bloom.bloom_api_call("DELETE", f"{items}/{case['tc_id']}", self.admin).status,
        ]
        self.assertEqual(
            removed,
            [values.STATUS_NOT_FOUND, values.STATUS_NO_CONTENT, [], values.STATUS_NOT_FOUND],
            msg=values.MSG_PID_ITEM_REMOVED,
            abort_on_fail=False,
            method="DELETE",
            endpoint=items,
        )

    def bud_a_test_case_of_another_project_is_refused_404(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PID_PREFIXES[2])
        other = self.bloom.bloom_api_new_project(self.admin, values.PID_PREFIXES[3])
        foreign = self.bloom.bloom_api_add_test_case(self.admin, other["id"], "Foreign").body
        suite = self.bloom.bloom_api_add_suite(self.admin, project["id"], "Demo", [])
        answer = self.bloom.bloom_api_call(
            "POST",
            f"/api/test-suites/{suite['suite_id']}/items",
            self.admin,
            params={"test_case_id": foreign["tc_id"]},
        )
        self.assertEqual(
            (answer.status, answer.body["detail"]),
            (values.STATUS_NOT_FOUND, "Test case not found in suite project"),
            msg=values.MSG_PID_FOREIGN,
            abort_on_fail=False,
        )

    def bud_a_campaign_and_its_items_use_public_ids_only(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PID_PREFIXES[4])
        case = self.bloom.bloom_api_add_test_case(self.admin, project["id"], "Case").body
        campaign = self.bloom.bloom_api_call(
            "POST", "/api/campaigns", self.admin, json={"project_id": project["id"], "name": "Demo"}
        ).body
        public, by_number = (
            f"/api/campaigns/{campaign['campaign_id']}",
            f"/api/campaigns/{campaign['id']}",
        )
        self.assertEqual(
            (
                bool(re.fullmatch(rf"{project['prefix']}-CMP-\d{{3,}}", campaign["campaign_id"])),
                self.bloom.bloom_api_call("GET", public, self.admin).body["id"],
            ),
            (True, campaign["id"]),
            msg=values.MSG_PID_CAMPAIGN_ID,
            abort_on_fail=False,
            method="GET",
            endpoint=public,
        )
        for method, body in (("GET", None), ("PATCH", {"name": "Renamed"}), ("DELETE", None)):
            answer = self.bloom.bloom_api_call(method, by_number, self.admin, json=body)
            self.assertEqual(
                (answer.status, answer.body["detail"]),
                (values.STATUS_NOT_FOUND, "Campaign not found"),
                msg=values.MSG_PID_CAMPAIGN_NUMBER.format(method=method),
                abort_on_fail=False,
                method=method,
                endpoint=by_number,
            )
        numbered = self.bloom.bloom_api_call(
            "POST", f"{public}/items", self.admin, params={"test_case_id": case["id"]}
        )
        added = self.bloom.bloom_api_call(
            "POST", f"{public}/items", self.admin, params={"test_case_id": case["tc_id"]}
        )
        item = f"{public}/items/{case['tc_id']}"
        by_item_number = self.bloom.bloom_api_call(
            "PATCH", f"{public}/items/{added.body['id']}", self.admin, json={"comment": "x"}
        )
        commented = self.bloom.bloom_api_call(
            "PATCH", item, self.admin, json={"comment": "Checked"}
        )
        self.assertEqual(
            (
                numbered.status,
                added.status,
                by_item_number.status,
                commented.status,
                (commented.body["id"], commented.body["comment"]),
                self.bloom.bloom_api_call("DELETE", item, self.admin).status,
                self.bloom.bloom_api_call("GET", public, self.admin).body["items"],
                self.bloom.bloom_api_call("DELETE", item, self.admin).status,
            ),
            (
                values.STATUS_NOT_FOUND,
                values.STATUS_CREATED,
                values.STATUS_NOT_FOUND,
                values.STATUS_OK,
                (added.body["id"], "Checked"),
                values.STATUS_NO_CONTENT,
                [],
                values.STATUS_NOT_FOUND,
            ),
            msg=values.MSG_PID_CAMPAIGN_ITEM,
            abort_on_fail=False,
            method="PATCH",
            endpoint=item,
        )
        self.assertEqual(
            (
                self.bloom.bloom_api_call("DELETE", public, self.admin).status,
                self.bloom.bloom_api_call("GET", public, self.admin).status,
            ),
            (values.STATUS_NO_CONTENT, values.STATUS_NOT_FOUND),
            msg=values.MSG_PID_CAMPAIGN_DELETED,
            abort_on_fail=False,
            method="DELETE",
            endpoint=public,
        )

    def bud_the_document_address_uses_public_ids(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PID_PREFIXES[5])
        suite = self.bloom.bloom_api_add_suite(self.admin, project["id"], "Demo", [])
        campaign = self.bloom.bloom_api_call(
            "POST", "/api/campaigns", self.admin, json={"project_id": project["id"], "name": "Demo"}
        ).body
        case = self.bloom.bloom_api_add_test_case(self.admin, project["id"], "Case").body
        docs = f"/api/projects/{project['prefix']}/docs"
        for slug, row, key in (
            ("test-suites", suite, "suite_id"),
            ("campaigns", campaign, "campaign_id"),
        ):
            opened = self.bloom.bloom_api_call("GET", f"{docs}/{slug}/{row[key]}", self.admin)
            numbered = self.bloom.bloom_api_call("GET", f"{docs}/{slug}/{row['id']}", self.admin)
            self.assertEqual(
                (opened.status, opened.body["id"], opened.body["doc_id"], numbered.status),
                (values.STATUS_OK, row["id"], row[key], values.STATUS_NOT_FOUND),
                msg=values.MSG_PID_ADDRESS.format(slug=slug),
                abort_on_fail=False,
                method="GET",
                endpoint=f"{docs}/{slug}",
            )
        opened = self.bloom.bloom_api_call("GET", f"{docs}/test-cases/{case['id']}", self.admin)
        self.assertEqual(
            (opened.status, opened.body["doc_id"]),
            (values.STATUS_OK, case["tc_id"]),
            msg=values.MSG_PID_CASE_ADDRESS,
            abort_on_fail=False,
        )
