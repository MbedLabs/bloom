"""
* @file     ${tests/api/requirements_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests creating, reading, changing and deleting a requirement over HTTP.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the requirement round trip.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class RequirementsHttpBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_requirement_goes_through_its_whole_round_trip(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(
            self.admin, values.REQH_PREFIXES[0], description="test"
        )
        listing = {"project_id": project["id"]}
        empty = self.bloom.bloom_api_call("GET", "/api/requirements", self.admin, params=listing)
        self.assertEqual(
            (empty.status, empty.body["items"]),
            (values.STATUS_OK, []),
            msg=values.MSG_REQH_EMPTY,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/requirements",
        )
        created = self.bloom.bloom_api_call(
            "POST", "/api/requirements", self.admin, json={**listing, "title": "System shall boot"}
        )
        self.print_variables({"created": created.body})
        self.assertEqual(
            (
                created.status,
                created.body["title"],
                created.body["req_id"].startswith(f"{project['prefix']}-REQ-"),
            ),
            (values.STATUS_CREATED, "System shall boot", True),
            msg=values.MSG_REQH_CREATED,
            abort_on_fail=False,
            method="POST",
            endpoint="/api/requirements",
        )
        path = f"/api/requirements/{created.body['id']}"
        listed = self.bloom.bloom_api_call("GET", "/api/requirements", self.admin, params=listing)
        read = self.bloom.bloom_api_call("GET", path, self.admin)
        self.assertEqual(
            (listed.status, len(listed.body["items"]), read.status, read.body["req_id"]),
            (values.STATUS_OK, 1, values.STATUS_OK, created.body["req_id"]),
            msg=values.MSG_REQH_READ,
            abort_on_fail=False,
            method="GET",
            endpoint=path,
        )
        updated = self.bloom.bloom_api_call(
            "PATCH", path, self.admin, json={"title": "Updated title"}
        )
        self.assertEqual(
            (updated.status, updated.body["title"]),
            (values.STATUS_OK, "Updated title"),
            msg=values.MSG_REQH_UPDATED,
            abort_on_fail=False,
            method="PATCH",
            endpoint=path,
        )
        deleted = self.bloom.bloom_api_call("DELETE", path, self.admin)
        self.assertIn(
            deleted.status,
            (values.STATUS_OK, values.STATUS_NO_CONTENT),
            msg=values.MSG_REQH_DELETED,
            abort_on_fail=False,
            method="DELETE",
            endpoint=path,
        )

    def bud_a_test_case_keeps_its_editor_body(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(
            self.admin, values.REQH_PREFIXES[1], description="test"
        )
        created = self.bloom.bloom_api_add_test_case(
            self.admin,
            project["id"],
            "Boot time",
            content_json=values.REQH_BODY,
            content_html=values.REQH_HTML,
        )
        self.assertEqual(
            (created.status, created.body["content_json"]),
            (values.STATUS_CREATED, values.REQH_BODY),
            msg=values.MSG_REQH_BODY_CREATED,
            abort_on_fail=False,
            method="POST",
            endpoint="/api/test-cases",
        )
        listed = self.bloom.bloom_api_call(
            "GET", "/api/test-cases", self.admin, params={"project_id": project["id"]}
        )
        read = self.bloom.bloom_api_call("GET", f"/api/test-cases/{created.body['id']}", self.admin)
        self.assertEqual(
            (listed.body["items"][0]["content_json"], read.body["content_html"]),
            (values.REQH_BODY, values.REQH_HTML),
            msg=values.MSG_REQH_BODY_READ,
            abort_on_fail=False,
            method="GET",
            endpoint="/api/test-cases",
        )
