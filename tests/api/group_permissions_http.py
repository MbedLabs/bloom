"""
* @file     ${tests/api/group_permissions_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests explicit project policies and whole artefact scopes over HTTP.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the group permissions over HTTP.
"""

import re

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class GroupPermissionsHttpBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_a_read_only_group_reads_but_cannot_write(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        user = self.bloom.bloom_api_scenario_user(self.admin, "maintainer", [project], "Read Only")
        listed = self.bloom.bloom_api_call(
            "GET", "/api/requirements", user.headers, params={"project_id": project}
        ).status
        denied = self.bloom.bloom_api_make(user.headers, "requirements", project)
        mine = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/permissions", user.headers
        ).body
        self.assertEqual(
            (listed, denied.status, denied.body["detail"], mine["REQ"], "member" in mine),
            (
                values.STATUS_OK,
                values.STATUS_FORBIDDEN,
                "Missing permission: create on REQ.",
                ["view"],
                False,
            ),
            msg=values.MSG_GP_READ_ONLY,
            abort_on_fail=False,
        )

    def bud_a_group_policy_adds_to_an_external_role(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        user = self.bloom.bloom_api_scenario_user(self.admin, "external", [project], "Test Author")
        created = self.bloom.bloom_api_make(user.headers, "test-cases", project).status
        denied = self.bloom.bloom_api_make(user.headers, "requirements", project)
        self.assertEqual(
            (created, denied.status, denied.body["detail"]),
            (values.STATUS_CREATED, values.STATUS_FORBIDDEN, "Missing permission: create on REQ."),
            msg=values.MSG_GP_EXTERNAL_ROLE,
            abort_on_fail=False,
        )

    def bud_a_project_content_grant_cannot_manage_access(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        user = self.bloom.bloom_api_new_member(
            self.admin, self.bloom.bloom_api_next_name("content-admin").replace(" ", "-")
        )
        other = self.bloom.bloom_api_new_member(
            self.admin, self.bloom.bloom_api_next_name("other").replace(" ", "-")
        )
        policy = self.bloom.bloom_api_new_policy(
            self.admin, self.bloom.bloom_api_next_name("Everything"), {"*": ["*"]}
        )
        membership = self.bloom.bloom_api_admit(
            self.admin, project, user.id, policy_ids=[policy["id"]]
        ).body["id"]
        self.bloom.bloom_api_grant_scenario(self.admin, "Project Administrator", user.id, project)
        created = self.bloom.bloom_api_make(user.headers, "requirements", project).status
        mine = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/permissions", user.headers
        ).body
        self.assertEqual(
            (created, "member" in mine),
            (values.STATUS_CREATED, False),
            msg=values.MSG_GP_CONTENT_GRANT,
            abort_on_fail=False,
        )
        base = f"/api/projects/{project}"
        for method, path, body in (
            ("GET", f"{base}/members", None),
            ("POST", f"{base}/members", {"user_id": other.id, "role": "maintainer"}),
            ("GET", f"{base}/members/{membership}", None),
            ("PATCH", f"{base}/members/{membership}", {"role": "external"}),
            ("DELETE", f"{base}/members/{membership}", None),
            ("GET", f"{base}/access", None),
        ):
            denied = self.bloom.bloom_api_call(method, path, user.headers, json=body)
            self.assertEqual(
                (denied.status, denied.body["detail"]),
                (values.STATUS_FORBIDDEN, "Application permission is required"),
                msg=values.MSG_GP_MANAGE_ACCESS.format(method=method, path=path),
                abort_on_fail=False,
            )
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", f"{base}/members", self.admin).status,
                self.bloom.bloom_api_call("GET", f"{base}/access", self.admin).status,
            ),
            (values.STATUS_OK, values.STATUS_OK),
            msg=values.MSG_GP_ADMIN_MANAGES,
            abort_on_fail=False,
        )

    def bud_no_access_and_the_administrator(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        user = self.bloom.bloom_api_new_member(
            self.admin, self.bloom.bloom_api_next_name("no-access").replace(" ", "-")
        )
        denied = self.bloom.bloom_api_make(user.headers, "requirements", project)
        self.assertEqual(
            (
                denied.status,
                denied.body["detail"],
                self.bloom.bloom_api_call(
                    "GET", f"/api/projects/{project}/permissions", user.headers
                ).body,
                self.bloom.bloom_api_call(
                    "GET", f"/api/projects/{project}/permissions", self.admin
                ).body,
                self.bloom.bloom_api_call(
                    "GET", f"/api/projects/{project}/members", self.admin
                ).status,
            ),
            (
                values.STATUS_FORBIDDEN,
                "User is not assigned to this project.",
                {},
                {"*": ["*"]},
                values.STATUS_OK,
            ),
            msg=values.MSG_GP_NO_ACCESS,
            abort_on_fail=False,
        )

    def bud_policy_rules_are_checked_on_update_400(self):
        values = self.parameters
        body = {
            "name": self.bloom.bloom_api_next_name("Policy"),
            "description": "Bad rules",
            "rules": {"widget": {"read": True}},
        }
        created = self.bloom.bloom_api_call("POST", "/api/policies", self.admin, json=body)
        body["rules"] = {"REQ": {"read": True, "visibility": ["internal"]}}
        policy = self.bloom.bloom_api_call("POST", "/api/policies", self.admin, json=body).body
        patched = self.bloom.bloom_api_call(
            "PATCH",
            f"/api/policies/{policy['id']}",
            self.admin,
            json={"rules": {"REQ": {"write": True}}},
        )
        self.assertEqual(
            ((created.status, created.body["detail"]), (patched.status, patched.body["detail"])),
            (
                (values.STATUS_BAD_REQUEST, "Unknown resources: ['widget']"),
                (values.STATUS_BAD_REQUEST, "Choose at least one tag for REQ."),
            ),
            msg=values.MSG_GP_RULES_CHECKED,
            abort_on_fail=False,
        )

    def bud_the_access_report_leaves_out_replaced_group_rules(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        other = self.bloom.bloom_api_next_project(self.admin)["id"]
        direct = self.bloom.bloom_api_new_member(
            self.admin, self.bloom.bloom_api_next_name("direct").replace(" ", "-")
        )
        grouped = self.bloom.bloom_api_new_member(
            self.admin, self.bloom.bloom_api_next_name("grouped").replace(" ", "-")
        )
        policy = self.bloom.bloom_api_new_policy(
            self.admin, self.bloom.bloom_api_next_name("Everything"), {"*": ["*"]}
        )
        self.bloom.bloom_api_admit(self.admin, project, direct.id, policy_ids=[policy["id"]])
        self.bloom.bloom_api_grant_scenario(self.admin, "Test Author", direct.id, project)
        self.bloom.bloom_api_grant_scenario(self.admin, "Test Author", grouped.id, project)
        access = self.bloom.bloom_api_call("GET", f"/api/projects/{project}/access", self.admin)
        by_user = {entry["user_id"]: entry["origins"] for entry in access.body}
        elsewhere = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{other}/access", self.admin
        ).body
        self.assertEqual(
            (
                access.status,
                [origin["kind"] for origin in by_user[direct.id]],
                all(origin["policies"] and not origin["owner"] for origin in by_user[direct.id]),
                by_user[grouped.id][0]["kind"],
                by_user[grouped.id][0]["policies"][0].startswith("Test Author "),
                any(entry["user_id"] in {direct.id, grouped.id} for entry in elsewhere),
                self.bloom.bloom_api_call(
                    "GET", f"/api/projects/{project}/access", direct.headers
                ).status,
            ),
            (values.STATUS_OK, ["direct"], True, "group", True, False, values.STATUS_FORBIDDEN),
            msg=values.MSG_GP_ACCESS_REPORT,
            abort_on_fail=False,
        )

    def bud_document_permissions_follow_the_document_type(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        user = self.bloom.bloom_api_permission_user(
            self.admin, {"SPEC": ["view", "edit"], "PRT": ["view"]}, project
        )
        specification = self.bloom.bloom_api_make(
            self.admin, "documents", project, doc_type="SPEC"
        ).body["id"]
        protocol = self.bloom.bloom_api_make(self.admin, "documents", project, doc_type="PRT").body[
            "id"
        ]
        edited = self.bloom.bloom_api_call(
            "PATCH", f"/api/documents/{specification}", user.headers, json={"title": "Edited"}
        ).status
        denied = self.bloom.bloom_api_call(
            "PATCH", f"/api/documents/{protocol}", user.headers, json={"title": "Edited"}
        )
        retyped = self.bloom.bloom_api_call(
            "PATCH", f"/api/documents/{specification}", user.headers, json={"doc_type": "PRT"}
        )
        self.assertEqual(
            (
                edited,
                (denied.status, denied.body["detail"]),
                (retyped.status, retyped.body["detail"]),
            ),
            (
                values.STATUS_OK,
                (values.STATUS_FORBIDDEN, "Missing permission: edit on PRT."),
                (values.STATUS_FORBIDDEN, "Missing permission: edit on PRT."),
            ),
            msg=values.MSG_GP_DOCUMENT_TYPE,
            abort_on_fail=False,
        )

    def bud_an_external_user_cannot_change_what_they_cannot_see_404(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        requirement = self.bloom.bloom_api_make(self.admin, "requirements", project).body
        test_case = self.bloom.bloom_api_make(self.admin, "test-cases", project).body
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "Requirements Author", "Test Author"
        )
        answers = []
        for kind, row in (("requirements", requirement), ("test-cases", test_case)):
            answers.append(
                self.bloom.bloom_api_call(
                    "PATCH", f"/api/{kind}/{row['id']}", user.headers, json={"title": "x"}
                ).status
            )
            answers.append(
                self.bloom.bloom_api_call("DELETE", f"/api/{kind}/{row['id']}", user.headers).status
            )
        kept = self.bloom.bloom_api_call(
            "GET", f"/api/requirements/{requirement['id']}", self.admin
        ).body["title"]
        self.assertEqual(
            (requirement["visibility"], answers, kept),
            ("internal", [values.STATUS_NOT_FOUND] * 4, requirement["title"]),
            msg=values.MSG_GP_UNSEEN_UNCHANGED,
            abort_on_fail=False,
        )

    def bud_a_user_outside_the_project_gets_404_by_id(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        requirement = self.bloom.bloom_api_make(self.admin, "requirements", project).body["id"]
        user = self.bloom.bloom_api_new_member(
            self.admin, self.bloom.bloom_api_next_name("outside").replace(" ", "-")
        )
        edited = self.bloom.bloom_api_call(
            "PATCH", f"/api/requirements/{requirement}", user.headers, json={"title": "x"}
        )
        self.assertEqual(
            (edited.status, edited.body["detail"]),
            (values.STATUS_NOT_FOUND, "Requirement not found"),
            msg=values.MSG_GP_OUTSIDE,
            abort_on_fail=False,
        )

    def bud_every_change_by_id_hides_what_an_external_user_cannot_see(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        defect = self.bloom.bloom_api_make(self.admin, "defects", project).body["id"]
        campaign = self.bloom.bloom_api_make(self.admin, "campaigns", project).body["campaign_id"]
        suite = self.bloom.bloom_api_make(self.admin, "test-suites", project).body["suite_id"]
        test_case = self.bloom.bloom_api_make(self.admin, "test-cases", project).body["tc_id"]
        document = self.bloom.bloom_api_make(self.admin, "documents", project).body["id"]
        section = self.bloom.bloom_api_call(
            "POST", f"/api/documents/{document}/sections", self.admin, json={"title": "Scope"}
        ).body["id"]
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], *values.GP_EXTERNAL_AUTHOR
        )
        own_campaign = self.bloom.bloom_api_make(user.headers, "campaigns", project)
        attempts = [
            ("PATCH", f"/api/defects/{defect}", {"title": "x"}),
            ("POST", f"/api/defects/{defect}/refresh-external", None),
            ("DELETE", f"/api/defects/{defect}", None),
            ("PATCH", f"/api/campaigns/{campaign}", {"name": "x"}),
            ("POST", f"/api/campaigns/{campaign}/items?test_case_id={test_case}", None),
            ("DELETE", f"/api/campaigns/{campaign}", None),
            ("POST", f"/api/test-suites/{suite}/items?test_case_id={test_case}", None),
            ("PATCH", f"/api/documents/{document}", {"title": "x"}),
            ("POST", f"/api/documents/{document}/sections", {"title": "x"}),
            ("PATCH", f"/api/document-sections/{section}", {"title": "x"}),
            ("POST", f"/api/documents/{document}/sections/reorder", {"section_orders": []}),
            ("DELETE", f"/api/document-sections/{section}", None),
            (
                "POST",
                f"/api/campaigns/{own_campaign.body['campaign_id']}/items?test_case_id={test_case}",
                None,
            ),
        ]
        self.assertEqual(
            own_campaign.status,
            values.STATUS_CREATED,
            msg=values.MSG_GP_OWN_CAMPAIGN,
            abort_on_fail=False,
        )
        for method, path, body in attempts:
            answer = self.bloom.bloom_api_call(method, path, user.headers, json=body)
            self.assertEqual(
                (answer.status, answer.body["detail"] != "Not Found"),
                (values.STATUS_NOT_FOUND, True),
                msg=values.MSG_GP_HIDDEN_BY_ID.format(method=method, path=path),
                abort_on_fail=False,
            )

    def bud_an_external_user_changes_only_customer_rows_they_created(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        shared = self.bloom.bloom_api_make(
            self.admin, "test-cases", project, visibility="customer"
        ).body["id"]
        user = self.bloom.bloom_api_scenario_user(self.admin, "external", [project], "Test Author")
        own = self.bloom.bloom_api_make(user.headers, "test-cases", project).body["id"]
        edited = self.bloom.bloom_api_call(
            "PATCH", f"/api/test-cases/{own}", user.headers, json={"title": "Renamed"}
        )
        refused = self.bloom.bloom_api_call(
            "PATCH", f"/api/test-cases/{shared}", user.headers, json={"title": "Renamed"}
        )
        self.assertEqual(
            ((edited.status, edited.body["title"]), (refused.status, refused.body["detail"])),
            ((values.STATUS_OK, "Renamed"), (values.STATUS_FORBIDDEN, values.GP_ONLY_OWN)),
            msg=values.MSG_GP_OWN_ROWS,
            abort_on_fail=False,
        )

    def bud_an_item_of_a_hidden_campaign_is_not_found(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        case = self.bloom.bloom_api_make(self.admin, "test-cases", project).body
        campaign = self.bloom.bloom_api_make(
            self.admin, "campaigns", project, test_case_ids=[case["id"]]
        ).body["campaign_id"]
        user = self.bloom.bloom_api_scenario_user(self.admin, "external", [project], "Test Author")
        changed = self.bloom.bloom_api_call(
            "PATCH",
            f"/api/campaigns/{campaign}/items/{case['tc_id']}",
            user.headers,
            json={"comment": "x"},
        )
        self.assertEqual(
            (changed.status, changed.body["detail"]),
            (values.STATUS_NOT_FOUND, "Campaign not found"),
            msg=values.MSG_GP_HIDDEN_CAMPAIGN,
            abort_on_fail=False,
        )

    def bud_a_request_body_cannot_reach_a_hidden_artefact(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        hidden_case = self.bloom.bloom_api_make(self.admin, "test-cases", project).body["id"]
        shown_case = self.bloom.bloom_api_make(
            self.admin, "test-cases", project, visibility="customer"
        ).body["id"]
        hidden_suite = self.bloom.bloom_api_make(self.admin, "test-suites", project).body["id"]
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "Requirements Author", "Test Author"
        )
        suite = self.bloom.bloom_api_make(
            user.headers, "test-suites", project, test_case_ids=[hidden_case, shown_case]
        )
        campaign = self.bloom.bloom_api_make(
            user.headers, "campaigns", project, suite_ids=[hidden_suite]
        )
        self.assertEqual(
            (
                suite.status,
                [item["test_case_id"] for item in suite.body["items"]],
                campaign.status,
                campaign.body["detail"],
            ),
            (
                values.STATUS_CREATED,
                [shown_case],
                values.STATUS_NOT_FOUND,
                f"Suite {hidden_suite} not found",
            ),
            msg=values.MSG_GP_BODY_REACH,
            abort_on_fail=False,
        )

    def bud_a_campaign_update_keeps_suites_the_editor_cannot_see(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        hidden, first, second = (
            self.bloom.bloom_api_make(self.admin, "test-suites", project, visibility=vis).body["id"]
            for vis in ("internal", "customer", "customer")
        )
        user = self.bloom.bloom_api_scenario_user(self.admin, "external", [project], "Test Author")
        campaign = self.bloom.bloom_api_make(user.headers, "campaigns", project).body["campaign_id"]
        self.bloom.bloom_api_call(
            "PATCH", f"/api/campaigns/{campaign}", self.admin, json={"suite_ids": [hidden, first]}
        )
        updated = self.bloom.bloom_api_call(
            "PATCH", f"/api/campaigns/{campaign}", user.headers, json={"suite_ids": [second]}
        ).status
        linked = sorted(
            s["id"]
            for s in self.bloom.bloom_api_call(
                "GET", f"/api/campaigns/{campaign}", self.admin
            ).body["suites"]
        )
        self.assertEqual(
            (updated, linked),
            (values.STATUS_OK, sorted([hidden, second])),
            msg=values.MSG_GP_KEEPS_HIDDEN_SUITES,
            abort_on_fail=False,
        )

    def bud_an_empty_suite_list_keeps_suites_outside_the_allowed_types(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        suite = self.bloom.bloom_api_make(
            self.admin, "test-suites", project, visibility="customer"
        ).body["id"]
        user = self.bloom.bloom_api_permission_user(
            self.admin,
            {"CMP": ["view", "create", "edit", "plan"]},
            project,
            role="external",
            scope=["CMP"],
        )
        campaign = self.bloom.bloom_api_make(user.headers, "campaigns", project).body["campaign_id"]
        self.bloom.bloom_api_call(
            "PATCH", f"/api/campaigns/{campaign}", self.admin, json={"suite_ids": [suite]}
        )
        updated = self.bloom.bloom_api_call(
            "PATCH", f"/api/campaigns/{campaign}", user.headers, json={"suite_ids": []}
        ).status
        linked = [
            s["id"]
            for s in self.bloom.bloom_api_call(
                "GET", f"/api/campaigns/{campaign}", self.admin
            ).body["suites"]
        ]
        self.assertEqual(
            (updated, linked),
            (values.STATUS_OK, [suite]),
            msg=values.MSG_GP_EMPTY_SUITES,
            abort_on_fail=False,
        )

    def bud_a_copy_leaves_out_source_rows_the_user_cannot_see(self):
        values = self.parameters
        source = self.bloom.bloom_api_next_project(self.admin)["id"]
        target = self.bloom.bloom_api_next_project(self.admin)["id"]
        hidden = self.bloom.bloom_api_make(self.admin, "requirements", source).body["id"]
        shown = self.bloom.bloom_api_make(
            self.admin, "requirements", source, req_origin="customer"
        ).body["id"]
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [source, target], "Requirements Author"
        )
        copied = self.bloom.bloom_api_call(
            "POST",
            f"/api/projects/{target}/import",
            user.headers,
            json={"source_project_id": source, "doc_type": "REQ", "doc_ids": [hidden, shown]},
        )
        self.assertEqual(
            (copied.status, copied.body["imported"], copied.body["skipped"], copied.body["errors"]),
            (values.STATUS_CREATED, 1, 1, [f"Requirement {hidden} not found in source project"]),
            msg=values.MSG_GP_COPY_HIDDEN,
            abort_on_fail=False,
        )

    def bud_a_test_case_file_import_checks_edit_and_create_per_row(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        existing = self.bloom.bloom_api_make(self.admin, "test-cases", project).body
        content = f"tc_id,title\n{existing['tc_id']},Changed\n,Brand new\n".encode()
        upload = lambda who: self.bloom.bloom_api_import_file(
            who, project, "test-cases", "c.csv", content, "application/octet-stream", format="csv"
        )
        creator = self.bloom.bloom_api_permission_user(
            self.admin, {"TC": ["view", "import", "create"]}, project
        )
        created = upload(creator.headers)
        kept = self.bloom.bloom_api_call(
            "GET", f"/api/test-cases/{existing['id']}", self.admin
        ).body["title"]
        self.assertEqual(
            (
                created.status,
                (created.body["created"], created.body["updated"], created.body["skipped"]),
                created.body["errors"],
                kept,
            ),
            (values.STATUS_CREATED, (1, 0, 1), ["row 1: not permitted"], existing["title"]),
            msg=values.MSG_GP_IMPORT_CREATE_ONLY,
            abort_on_fail=False,
        )
        editor = self.bloom.bloom_api_permission_user(
            self.admin, {"TC": ["view", "import", "edit"]}, project
        )
        edited = upload(editor.headers)
        changed = self.bloom.bloom_api_call(
            "GET", f"/api/test-cases/{existing['id']}", self.admin
        ).body["title"]
        self.assertEqual(
            (
                edited.status,
                (edited.body["created"], edited.body["updated"], edited.body["skipped"]),
                edited.body["errors"],
                changed,
            ),
            (values.STATUS_CREATED, (0, 1, 1), ["row 2: not permitted"], "Changed"),
            msg=values.MSG_GP_IMPORT_EDIT_ONLY,
            abort_on_fail=False,
        )

    def bud_a_test_case_file_import_treats_a_hidden_test_case_as_new(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        hidden = self.bloom.bloom_api_make(self.admin, "test-cases", project).body
        user = self.bloom.bloom_api_scenario_user(self.admin, "external", [project], "Test Author")
        content = f"tc_id,title\n{hidden['tc_id']},Taken over\n".encode()
        imported = self.bloom.bloom_api_import_file(
            user.headers,
            project,
            "test-cases",
            "c.csv",
            content,
            "application/octet-stream",
            format="csv",
        )
        kept = self.bloom.bloom_api_call("GET", f"/api/test-cases/{hidden['id']}", self.admin).body[
            "title"
        ]
        self.assertEqual(
            (
                imported.status,
                imported.body["created"],
                imported.body["updated"],
                imported.body["new_ids"] != [hidden["tc_id"]],
                kept,
            ),
            (values.STATUS_CREATED, 1, 0, True, hidden["title"]),
            msg=values.MSG_GP_IMPORT_HIDDEN_NEW,
            abort_on_fail=False,
        )

    def bud_a_testrail_import_neither_reuses_nor_links_hidden_rows(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        hidden = self.bloom.bloom_api_make(self.admin, "requirements", project).body["req_id"]
        external = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "Test Author", "Requirements Author"
        )
        shown = self.bloom.bloom_api_make(external.headers, "requirements", project).body["req_id"]
        export = (
            "<suite><sections><section><name>Boot</name><cases><case><id>C1</id>"
            f"<title>Cold boot</title><references>{hidden}, {shown}</references>"
            "</case></cases></section></sections></suite>"
        ).encode()

        def run(who):
            body = self.bloom.bloom_api_import_file(
                who, project, "testrail", "t.xml", export, "application/octet-stream", format="xml"
            ).body
            return (
                body["created"],
                body["updated"],
                body["links_created"],
                len(body["suites_created"]),
            )

        self.assertEqual(
            (run(self.admin), run(external.headers), run(self.admin)),
            ((1, 0, 2, 1), (1, 0, 1, 1), (0, 1, 0, 0)),
            msg=values.MSG_GP_TESTRAIL_HIDDEN,
            abort_on_fail=False,
        )

    def bud_a_reqif_import_does_not_reuse_hidden_requirements(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]

        def run(who):
            body = self.bloom.bloom_api_import_file(
                who, project, "reqif", "s.reqif", values.GP_REQIF, "application/octet-stream"
            ).body
            return body["imported"], body["skipped"], body["links_created"]

        first = run(self.admin)
        external = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "Requirements Author"
        )
        self.assertEqual(
            (first, run(external.headers), run(self.admin)),
            ((2, 0, 1), (2, 0, 1), (0, 2, 0)),
            msg=values.MSG_GP_REQIF_HIDDEN,
            abort_on_fail=False,
        )

    def bud_a_markdown_import_does_not_count_hidden_rows_as_duplicates(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        document = f"## [TC] {self.bloom.bloom_api_next_name('case')}\nPower the board\n".encode()

        def run(who):
            body = self.bloom.bloom_api_import_file(
                who, project, "markdown", "d.md", document, "application/octet-stream"
            ).body
            return body["artefacts_created"], body["artefacts_skipped"]

        first = run(self.admin)
        external = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "Test Author"
        )
        self.assertEqual(
            (first, run(external.headers), run(self.admin)),
            ((1, 0), (1, 0), (0, 1)),
            msg=values.MSG_GP_MARKDOWN_HIDDEN,
            abort_on_fail=False,
        )

    def bud_each_imported_row_needs_the_right_its_own_route_needs(self):
        values = self.parameters
        source = self.bloom.bloom_api_next_project(self.admin)["id"]
        target = self.bloom.bloom_api_next_project(self.admin)["id"]
        requirement = self.bloom.bloom_api_make(self.admin, "requirements", source).body
        copier = self.bloom.bloom_api_permission_user(
            self.admin, {"REQ": ["view", "import", "export"]}, source, target
        )
        copied = self.bloom.bloom_api_call(
            "POST",
            f"/api/projects/{target}/import",
            copier.headers,
            json={"source_project_id": source, "doc_type": "REQ", "doc_ids": [requirement["id"]]},
        )
        self.assertEqual(
            (copied.status, copied.body["errors"]),
            (values.STATUS_CREATED, [f"Requirement {requirement['id']}: not permitted"]),
            msg=values.MSG_GP_COPY_RIGHT,
            abort_on_fail=False,
        )
        reader = self.bloom.bloom_api_permission_user(
            self.admin, {"REQ": ["view", "import"]}, target
        )
        refused = self.bloom.bloom_api_import_file(
            reader.headers, target, "reqif", "s.reqif", values.GP_REQIF, "application/octet-stream"
        )
        self.assertEqual(
            (
                refused.status,
                refused.body["imported"],
                refused.body["skipped"],
                refused.body["errors"],
            ),
            (
                values.STATUS_CREATED,
                0,
                2,
                ["object OBJ-1: not permitted", "object OBJ-2: not permitted"],
            ),
            msg=values.MSG_GP_REQIF_RIGHT,
            abort_on_fail=False,
        )
        author = self.bloom.bloom_api_permission_user(
            self.admin, {"REQ": ["view", "import", "create"]}, target
        )
        unlinked = self.bloom.bloom_api_import_file(
            author.headers, target, "reqif", "s.reqif", values.GP_REQIF, "application/octet-stream"
        )
        self.assertEqual(
            (
                unlinked.status,
                unlinked.body["imported"],
                unlinked.body["links_created"],
                unlinked.body["errors"],
            ),
            (values.STATUS_CREATED, 2, 0, ["relation REL-1: not permitted"]),
            msg=values.MSG_GP_REQIF_LINK_RIGHT,
            abort_on_fail=False,
        )
        tester = self.bloom.bloom_api_permission_user(
            self.admin, {"REQ": ["view"], "TC": ["view", "import", "create"]}, source
        )
        export = (
            "<suite><sections><section><name>Boot</name><cases><case><id>C1</id>"
            f"<title>Cold boot</title><references>{requirement['req_id']}</references>"
            "</case></cases></section></sections></suite>"
        ).encode()
        railed = self.bloom.bloom_api_import_file(
            tester.headers,
            source,
            "testrail",
            "t.xml",
            export,
            "application/octet-stream",
            format="xml",
        ).body
        cases = self.bloom.bloom_api_call(
            "GET", "/api/test-cases", self.admin, params={"project_id": source}
        ).body["items"]
        imported = next(case for case in cases if case["tc_id"] == railed["new_ids"][0])
        self.assertEqual(
            (
                railed["created"],
                railed["links_created"],
                railed["suites_created"],
                railed["errors"],
                requirement["req_id"] in imported["description"],
            ),
            (
                1,
                0,
                [],
                ["case C1: links not permitted", "case C1: adding to suite Boot not permitted"],
                True,
            ),
            msg=values.MSG_GP_TESTRAIL_RIGHT,
            abort_on_fail=False,
        )
        title = self.bloom.bloom_api_next_name("case")
        document = f"## [TC] {title}\nPower the board\n".encode()
        marker = self.bloom.bloom_api_permission_user(
            self.admin, {"TC": ["view", "import"]}, target
        )
        marked = self.bloom.bloom_api_import_file(
            marker.headers, target, "markdown", "d.md", document, "application/octet-stream"
        )
        self.assertEqual(
            (
                marked.status,
                marked.body["artefacts_created"],
                marked.body["artefacts_skipped"],
                marked.body["errors"],
            ),
            (values.STATUS_CREATED, 0, 1, [f"section {title}: not permitted"]),
            msg=values.MSG_GP_MARKDOWN_RIGHT,
            abort_on_fail=False,
        )

    def bud_a_testrail_case_or_suite_without_its_right_is_reported(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]

        def export(*ids):
            cases = "".join(f"<case><id>{i}</id><title>Case {i}</title></case>" for i in ids)
            return f"<suite><sections><section><name>Boot</name><cases>{cases}</cases></section></sections></suite>".encode()

        planner = self.bloom.bloom_api_permission_user(
            self.admin, {"TC": ["view", "import", "create"], "TS": ["view", "plan"]}, project
        )
        planned = self.bloom.bloom_api_import_file(
            planner.headers,
            project,
            "testrail",
            "t.xml",
            export("C1"),
            "application/octet-stream",
            format="xml",
        )
        reader = self.bloom.bloom_api_permission_user(
            self.admin, {"TC": ["view", "import"]}, project
        )
        refused = self.bloom.bloom_api_import_file(
            reader.headers,
            project,
            "testrail",
            "t.xml",
            export("C1", "C2"),
            "application/octet-stream",
            format="xml",
        ).body
        self.assertEqual(
            (
                (
                    planned.status,
                    planned.body["created"],
                    planned.body["suites_created"],
                    planned.body["errors"],
                ),
                (refused["created"], refused["updated"], refused["skipped"], refused["errors"]),
            ),
            (
                (values.STATUS_CREATED, 1, [], ["case C1: creating suite Boot not permitted"]),
                (0, 0, 2, ["case C1: not permitted", "case C2: not permitted"]),
            ),
            msg=values.MSG_GP_TESTRAIL_SUITE_RIGHT,
            abort_on_fail=False,
        )

    def bud_a_markdown_import_cannot_create_a_type_outside_its_scope_403(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        document = f"## [TC] {self.bloom.bloom_api_next_name('case')}\nPower the board\n".encode()
        outside = self.bloom.bloom_api_permission_user(
            self.admin,
            {"TC": ["view", "import", "create"]},
            project,
            role="external",
            scope=["REQ"],
        )
        accepted = self.bloom.bloom_api_import_file(
            self.admin, project, "markdown", "d.md", document, "application/octet-stream"
        ).status
        refused = self.bloom.bloom_api_import_file(
            outside.headers, project, "markdown", "d.md", document, "application/octet-stream"
        ).status
        cases = self.bloom.bloom_api_call(
            "GET", "/api/test-cases", self.admin, params={"project_id": project}
        ).body["items"]
        self.assertEqual(
            (accepted, refused, len(cases)),
            (values.STATUS_CREATED, values.STATUS_FORBIDDEN, 1),
            msg=values.MSG_GP_MARKDOWN_SCOPE,
            abort_on_fail=False,
        )

    def bud_adding_a_test_case_to_a_campaign_returns_the_item(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        planner = self.bloom.bloom_api_permission_user(
            self.admin, {"CMP": ["view", "plan"], "TC": ["view"]}, project
        )
        for who in (self.admin, planner.headers):
            case = self.bloom.bloom_api_make(self.admin, "test-cases", project).body
            campaign = self.bloom.bloom_api_make(self.admin, "campaigns", project).body
            added = self.bloom.bloom_api_call(
                "POST",
                f"/api/campaigns/{campaign['campaign_id']}/items?test_case_id={case['tc_id']}",
                who,
            )
            saved = self.bloom.bloom_api_call(
                "GET", f"/api/campaigns/{campaign['campaign_id']}", self.admin
            ).body["items"]
            self.assertEqual(
                (
                    added.status,
                    (added.body["campaign_id"], added.body["test_case_id"], added.body["status"]),
                    added.body["test_case"]["tc_id"],
                    [(item["id"], item["test_case_id"]) for item in saved],
                ),
                (
                    values.STATUS_CREATED,
                    (campaign["id"], case["id"], "Pending"),
                    case["tc_id"],
                    [(added.body["id"], case["id"])],
                ),
                msg=values.MSG_GP_CAMPAIGN_ITEM,
                abort_on_fail=False,
            )

    def bud_an_external_users_creations_are_customer_and_in_their_first_status(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], *values.GP_EXTERNAL_AUTHOR
        )
        made = lambda kind: self.bloom.bloom_api_make(user.headers, kind, project).body
        requirement, case, design, defect, campaign, suite = (
            made(kind)
            for kind in (
                "requirements",
                "test-cases",
                "designs",
                "defects",
                "campaigns",
                "test-suites",
            )
        )
        self.assertEqual(
            (
                (requirement["visibility"], requirement["req_origin"], requirement["status"]),
                case["visibility"],
                (design["visibility"], design["status"]),
                (defect["visibility"], defect["status"]),
                (campaign["visibility"], campaign["status"]),
                suite["visibility"],
            ),
            (
                ("customer", "Customer", "Draft"),
                "customer",
                ("customer", "Draft"),
                ("customer", "Open"),
                ("customer", "Planned"),
                "customer",
            ),
            msg=values.MSG_GP_EXTERNAL_CREATES,
            abort_on_fail=False,
        )
        for kind, extra, message in (
            ("test-cases", {"visibility": "internal"}, "create customer artefacts only"),
            ("requirements", {"req_origin": "Internal"}, "create customer artefacts only"),
            ("test-cases", {"status": "Approved"}, "create in status Draft"),
            ("defects", {"status": "Triaged"}, "create in status Open"),
        ):
            refused = self.bloom.bloom_api_make(user.headers, kind, project, **extra)
            self.assertEqual(
                (refused.status, message in refused.body["detail"]),
                (values.STATUS_FORBIDDEN, True),
                msg=values.MSG_GP_EXTERNAL_CREATE_REFUSED.format(message=message),
                abort_on_fail=False,
            )

    def bud_an_external_user_keeps_visibility_and_sets_only_draft(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], *values.GP_EXTERNAL_AUTHOR
        )
        case = self.bloom.bloom_api_make(user.headers, "test-cases", project).body["id"]
        requirement = self.bloom.bloom_api_make(user.headers, "requirements", project).body["id"]
        defect = self.bloom.bloom_api_make(user.headers, "defects", project).body["id"]
        change = lambda path, body: self.bloom.bloom_api_call(
            "PATCH", path, user.headers, json=body
        )
        review = change(f"/api/test-cases/{case}", {"status": "Review"})
        moved = self.bloom.bloom_api_call(
            "POST",
            f"/api/artefacts/test-case/{case}/requests",
            user.headers,
            json={"kind": "review"},
        ).status
        stored = self.bloom.bloom_api_call("GET", f"/api/test-cases/{case}", self.admin).body[
            "status"
        ]
        fixed = change(f"/api/defects/{defect}", {"status": "Triaged"})
        self.assertEqual(
            (
                change(f"/api/test-cases/{case}", {"visibility": "internal"}).status,
                change(f"/api/test-cases/{case}", {"visibility": "customer"}).status,
                change(f"/api/requirements/{requirement}", {"req_origin": "Internal"}).status,
                (review.status, review.body["detail"]),
                moved,
                stored,
                change(f"/api/test-cases/{case}", {"status": "Draft"}).status,
                (fixed.status, "defects, risks, changes or campaigns" in fixed.body["detail"]),
            ),
            (
                values.STATUS_FORBIDDEN,
                values.STATUS_OK,
                values.STATUS_FORBIDDEN,
                (values.STATUS_FORBIDDEN, "External users set the status only to Draft."),
                values.STATUS_CREATED,
                "Review",
                values.STATUS_CONFLICT,
                (values.STATUS_FORBIDDEN, True),
            ),
            msg=values.MSG_GP_EXTERNAL_DRAFT_ONLY,
            abort_on_fail=False,
        )

    def bud_an_external_user_changes_no_part_of_what_others_created_403(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        customer = {"visibility": "customer"}
        case_row = self.bloom.bloom_api_make(self.admin, "test-cases", project, **customer).body
        case = case_row["id"]
        requirement = self.bloom.bloom_api_make(
            self.admin, "requirements", project, req_origin="Customer"
        ).body["id"]
        defect = self.bloom.bloom_api_make(self.admin, "defects", project, **customer).body["id"]
        suite = self.bloom.bloom_api_make(self.admin, "test-suites", project, **customer).body[
            "suite_id"
        ]
        campaign = self.bloom.bloom_api_make(
            self.admin, "campaigns", project, test_case_ids=[case], **customer
        ).body["campaign_id"]
        document = self.bloom.bloom_api_make(self.admin, "documents", project, **customer).body[
            "id"
        ]
        section = self.bloom.bloom_api_call(
            "POST", f"/api/documents/{document}/sections", self.admin, json={"title": "Scope"}
        ).body["id"]
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], *values.GP_EXTERNAL_AUTHOR
        )
        item = case_row["tc_id"]
        attempts = [
            ("PATCH", f"/api/test-cases/{case}", {"title": "x"}),
            ("DELETE", f"/api/test-cases/{case}", None),
            ("POST", f"/api/requirements/{requirement}/link-testrun", {"test_run_id": 1}),
            ("PATCH", f"/api/defects/{defect}", {"title": "x"}),
            ("POST", f"/api/defects/{defect}/refresh-external", None),
            ("POST", f"/api/test-suites/{suite}/items?test_case_id={item}", None),
            ("DELETE", f"/api/test-suites/{suite}", None),
            ("PATCH", f"/api/campaigns/{campaign}", {"name": "x"}),
            ("PATCH", f"/api/campaigns/{campaign}/items/{item}", {"comment": "x"}),
            ("DELETE", f"/api/campaigns/{campaign}/items/{item}", None),
            ("PATCH", f"/api/documents/{document}", {"title": "x"}),
            ("POST", f"/api/documents/{document}/sections", {"title": "x"}),
            ("PATCH", f"/api/document-sections/{section}", {"title": "x"}),
            ("DELETE", f"/api/document-sections/{section}", None),
        ]
        for method, path, body in attempts:
            answer = self.bloom.bloom_api_call(method, path, user.headers, json=body)
            detail = answer.body["detail"]
            named = detail == values.GP_ONLY_OWN or (
                method == "DELETE" and detail.startswith("Missing permission: delete on ")
            )
            self.assertEqual(
                (answer.status, named),
                (values.STATUS_FORBIDDEN, True),
                msg=values.MSG_GP_OTHERS_ROWS.format(method=method, path=path),
                abort_on_fail=False,
            )
        uploaded = self.bloom.bloom_api_upload_attachment(
            user.headers, document, "a.txt", b"x", "text/plain"
        )
        self.assertEqual(
            uploaded.status,
            values.STATUS_FORBIDDEN,
            msg=values.MSG_GP_OTHERS_ATTACHMENT,
            abort_on_fail=False,
        )

    def bud_a_type_outside_the_allowlist_answers_404_first(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        design = self.bloom.bloom_api_make(
            self.admin, "designs", project, visibility="customer"
        ).body["id"]
        reader = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "External Reader"
        )
        edited = self.bloom.bloom_api_call(
            "PATCH", f"/api/designs/{design}", reader.headers, json={"title": "x"}
        ).status
        self.assertEqual(
            edited, values.STATUS_NOT_FOUND, msg=values.MSG_GP_ALLOWLIST_FIRST, abort_on_fail=False
        )

    def bud_design_requests_check_creator_scope_and_review_authority(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        others = self.bloom.bloom_api_make(
            self.admin, "designs", project, visibility="customer"
        ).body["id"]
        hidden = self.bloom.bloom_api_make(self.admin, "designs", project).body["id"]
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "Design Author"
        )
        own = self.bloom.bloom_api_make(user.headers, "designs", project).body["id"]
        request = lambda design: self.bloom.bloom_api_call(
            "POST",
            f"/api/artefacts/design/{design}/requests",
            user.headers,
            json={"kind": "review"},
        )
        refused = request(others)
        path = f"/api/artefacts/design/{own}"
        bypass = self.bloom.bloom_api_call(
            "POST", path + "/transition", self.admin, json={"status": "Review"}
        ).status
        self.assertEqual(
            (
                request(hidden).status,
                (refused.status, refused.body["detail"]),
                bypass,
                request(own).status,
            ),
            (
                values.STATUS_NOT_FOUND,
                (
                    values.STATUS_FORBIDDEN,
                    "Only the document's assignee or an administrator requests review.",
                ),
                values.STATUS_CONFLICT,
                values.STATUS_CREATED,
            ),
            msg=values.MSG_GP_DESIGN_REQUEST,
            abort_on_fail=False,
        )
        creator = self.bloom.bloom_api_call(
            "POST", path + "/comments", user.headers, json={"body": "As creator"}
        ).status
        unassigned_reviewer = self.bloom.bloom_api_call(
            "POST", path + "/comments", self.admin, json={"body": "Holds review, not assigned"}
        ).status
        self.bloom.bloom_api_grant_scenario(self.admin, "Approver", user.id, project)
        unassigned = self.bloom.bloom_api_call(
            "POST", path + "/comments", user.headers, json={"body": "Unassigned"}
        ).status
        assigned = self.bloom.bloom_api_call(
            "PUT", path + "/workflow/assignees", self.admin, json={"reviewer_id": user.id}
        ).status
        reviewed = self.bloom.bloom_api_call(
            "POST", path + "/comments", user.headers, json={"body": "Reviewed"}
        ).status
        approval = self.bloom.bloom_api_call(
            "POST", path + "/requests", user.headers, json={"kind": "approval"}
        ).status
        denied = self.bloom.bloom_api_call(
            "POST", path + "/sign-off", user.headers, json={"step": "approve"}
        ).status
        rights = set(
            self.bloom.bloom_api_call(
                "GET", f"/api/projects/{project}/permissions", user.headers
            ).body["DES"]
        )
        self.assertEqual(
            (
                creator,
                unassigned_reviewer,
                unassigned,
                assigned,
                reviewed,
                approval,
                denied,
                "review" in rights,
                rights & {"approve", "delete"},
            ),
            (
                values.STATUS_CREATED,
                values.STATUS_FORBIDDEN,
                values.STATUS_CREATED,
                values.STATUS_OK,
                values.STATUS_CREATED,
                values.STATUS_CREATED,
                values.STATUS_FORBIDDEN,
                True,
                set(),
            ),
            msg=values.MSG_GP_DESIGN_REVIEW,
            abort_on_fail=False,
        )

    def bud_the_detail_read_names_the_changes_the_reader_may_make(self):
        values = self.parameters
        created = self.bloom.bloom_api_next_project(self.admin)
        project, prefix = created["id"], created["prefix"]
        others = self.bloom.bloom_api_make(
            self.admin, "designs", project, visibility="customer"
        ).body
        hidden = self.bloom.bloom_api_make(self.admin, "designs", project).body
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "Design Author"
        )
        own = self.bloom.bloom_api_make(user.headers, "designs", project).body
        reader = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "External Reader"
        )

        def actions(design, who):
            answer = self.bloom.bloom_api_call(
                "GET", f"/api/projects/{prefix}/docs/designs/{design['design_id']}", who
            )
            return answer.status, answer.body.get("allowed_actions")

        self.assertEqual(
            (
                actions(others, self.admin),
                actions(own, user.headers),
                actions(others, user.headers),
                actions(hidden, user.headers)[0],
                actions(others, reader.headers)[0],
            ),
            (
                (values.STATUS_OK, ["edit", "delete", "plan", "review", "approve", "comment"]),
                (values.STATUS_OK, ["edit", "comment"]),
                (values.STATUS_OK, []),
                values.STATUS_NOT_FOUND,
                values.STATUS_NOT_FOUND,
            ),
            msg=values.MSG_GP_ALLOWED_ACTIONS,
            abort_on_fail=False,
        )

    def bud_an_external_import_creates_customer_rows_and_touches_only_its_own(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        theirs = self.bloom.bloom_api_make(
            self.admin, "test-cases", project, visibility="customer"
        ).body
        self.bloom.bloom_api_call(
            "POST",
            "/api/test-suites",
            self.admin,
            json={"project_id": project, "name": "Boot", "visibility": "customer"},
        )
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], *values.GP_EXTERNAL_AUTHOR
        )
        content = (
            "tc_id,title,visibility,status\n"
            f"{theirs['tc_id']},Taken,,\n"
            ",Mine,,\n"
            ",Inside,internal,\n"
            ",Approved,,Approved\n"
        ).encode()
        rows = self.bloom.bloom_api_import_file(
            user.headers,
            project,
            "test-cases",
            "c.csv",
            content,
            "application/octet-stream",
            format="csv",
        ).body
        mine = [
            case["visibility"]
            for case in self.bloom.bloom_api_call(
                "GET", "/api/test-cases", user.headers, params={"project_id": project}
            ).body["items"]
            if case["title"] == "Mine"
        ]
        export = (
            "<suite><sections><section><name>Boot</name><cases>"
            "<case><id>C9</id><title>Rail</title></case>"
            "</cases></section></sections></suite>"
        ).encode()
        railed = self.bloom.bloom_api_import_file(
            user.headers,
            project,
            "testrail",
            "t.xml",
            export,
            "application/octet-stream",
            format="xml",
        ).body
        self.assertEqual(
            (
                (rows["created"], rows["updated"], rows["skipped"]),
                rows["errors"],
                mine,
                railed["created"],
                railed["errors"],
            ),
            (
                (1, 0, 3),
                ["row 1: not permitted", "row 3: not permitted", "row 4: not permitted"],
                ["customer"],
                1,
                ["case C9: adding to suite Boot not permitted"],
            ),
            msg=values.MSG_GP_EXTERNAL_IMPORT,
            abort_on_fail=False,
        )

    def bud_an_external_users_document_is_customer_and_a_draft(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], *values.GP_EXTERNAL_AUTHOR
        )
        created = self.bloom.bloom_api_make(user.headers, "documents", project)
        refused = self.bloom.bloom_api_make(
            user.headers, "documents", project, visibility="internal"
        )
        self.assertEqual(
            (
                (created.status, created.body["visibility"], created.body["status"]),
                (refused.status, refused.body["detail"]),
            ),
            (
                (values.STATUS_CREATED, "customer", "Draft"),
                (values.STATUS_FORBIDDEN, "External users create customer artefacts only."),
            ),
            msg=values.MSG_GP_EXTERNAL_DOCUMENT,
            abort_on_fail=False,
        )

    def bud_an_external_copy_reqif_or_markdown_import_creates_customer_rows(self):
        values = self.parameters
        source = self.bloom.bloom_api_next_project(self.admin)["id"]
        target = self.bloom.bloom_api_next_project(self.admin)["id"]
        case = self.bloom.bloom_api_make(
            self.admin, "test-cases", source, visibility="customer"
        ).body["id"]
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [source, target], "Requirements Author", "Test Author"
        )
        copied = self.bloom.bloom_api_call(
            "POST",
            f"/api/projects/{target}/import",
            user.headers,
            json={"source_project_id": source, "doc_type": "TC", "doc_ids": [case]},
        )
        reqif = self.bloom.bloom_api_import_file(
            user.headers, target, "reqif", "s.reqif", values.GP_REQIF, "application/octet-stream"
        ).body
        document = f"## [REQ] {self.bloom.bloom_api_next_name('r')}\nBody\n".encode()
        markdown = self.bloom.bloom_api_import_file(
            user.headers, target, "markdown", "d.md", document, "application/octet-stream"
        ).body
        cases = self.bloom.bloom_api_call(
            "GET", "/api/test-cases", self.admin, params={"project_id": target}
        ).body["items"]
        requirements = self.bloom.bloom_api_call(
            "GET", "/api/requirements", self.admin, params={"project_id": target}
        ).body["items"]
        self.assertEqual(
            (
                (copied.status, copied.body["imported"]),
                reqif["imported"],
                markdown["artefacts_created"],
                [(c["visibility"], c["status"]) for c in cases],
                len(requirements),
                {(r["visibility"], r["req_origin"], r["status"]) for r in requirements},
            ),
            (
                (values.STATUS_CREATED, 1),
                2,
                1,
                [("customer", "Draft")],
                3,
                {("customer", "Customer", "Draft")},
            ),
            msg=values.MSG_GP_EXTERNAL_COPY,
            abort_on_fail=False,
        )

    def bud_the_detail_read_follows_an_internal_users_permissions(self):
        values = self.parameters
        created = self.bloom.bloom_api_next_project(self.admin)
        project, prefix = created["id"], created["prefix"]
        design = self.bloom.bloom_api_make(self.admin, "designs", project).body

        def actions(policy):
            user = self.bloom.bloom_api_scenario_user(self.admin, "maintainer", [project], policy)
            return self.bloom.bloom_api_call(
                "GET", f"/api/projects/{prefix}/docs/designs/{design['design_id']}", user.headers
            ).body["allowed_actions"]

        self.assertEqual(
            (actions("Design Author"), actions("Read Only")),
            (["edit", "delete"], []),
            msg=values.MSG_GP_INTERNAL_ACTIONS,
            abort_on_fail=False,
        )

    def bud_status_edits_need_handoffs_and_separate_signoff_rights(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "maintainer", [project], "Requirements Author", "Design Author"
        )
        requirement = self.bloom.bloom_api_make(user.headers, "requirements", project).body["id"]
        path = f"/api/artefacts/requirement/{requirement}"
        reviewer = self.bloom.bloom_api_permission_user(
            self.admin, {"REQ": ["view", "review"]}, project
        )
        approver = self.bloom.bloom_api_permission_user(
            self.admin, {"REQ": ["view", "approve"]}, project
        )
        refused = self.bloom.bloom_api_call(
            "PATCH", f"/api/requirements/{requirement}", user.headers, json={"status": "Approved"}
        )
        unchanged = self.bloom.bloom_api_call(
            "GET", f"/api/requirements/{requirement}", self.admin
        ).body["status"]
        invalid = self.bloom.bloom_api_call(
            "PUT", path + "/workflow/assignees", self.admin, json={"reviewer_id": user.id}
        ).status
        assigned = self.bloom.bloom_api_call(
            "PUT",
            path + "/workflow/assignees",
            self.admin,
            json={"reviewer_id": reviewer.id, "approver_id": approver.id},
        ).status
        requested = self.bloom.bloom_api_call(
            "POST", path + "/requests", user.headers, json={"kind": "review"}
        ).status
        unauthorized = self.bloom.bloom_api_call(
            "POST", path + "/sign-off", user.headers, json={"step": "review"}
        ).status
        self.assertEqual(
            (
                (refused.status, refused.body["detail"]),
                unchanged,
                invalid,
                assigned,
                requested,
                unauthorized,
            ),
            (
                (values.STATUS_CONFLICT, "Use the document workflow for status changes."),
                "Draft",
                values.STATUS_UNPROCESSABLE,
                values.STATUS_OK,
                values.STATUS_CREATED,
                values.STATUS_FORBIDDEN,
            ),
            msg=values.MSG_GP_STATUS_HANDOFF,
            abort_on_fail=False,
        )
        comment = self.bloom.bloom_api_call(
            "POST",
            path + "/comments",
            reviewer.headers,
            json={"body": "Reviewed requested content"},
        ).status
        approval = self.bloom.bloom_api_call(
            "POST", path + "/requests", reviewer.headers, json={"kind": "approval"}
        ).status
        denied = [
            self.bloom.bloom_api_call(
                "POST", path + "/sign-off", who, json={"step": "approve"}
            ).status
            for who in (user.headers, reviewer.headers)
        ]
        approved = self.bloom.bloom_api_call(
            "POST", path + "/sign-off", approver.headers, json={"step": "approve"}
        )
        stored = self.bloom.bloom_api_call(
            "GET", f"/api/requirements/{requirement}", self.admin
        ).body["status"]
        rights = set(
            self.bloom.bloom_api_call(
                "GET", f"/api/projects/{project}/permissions", reviewer.headers
            ).body["REQ"]
        )
        self.assertEqual(
            (
                comment,
                approval,
                denied,
                approved.status,
                approved.body["reviewed_by_id"],
                approved.body["approved_by_id"],
                stored,
                "review" in rights,
                rights & {"create", "edit", "approve", "delete"},
            ),
            (
                values.STATUS_CREATED,
                values.STATUS_CREATED,
                [values.STATUS_FORBIDDEN] * 2,
                values.STATUS_OK,
                reviewer.id,
                approver.id,
                "Approved",
                True,
                set(),
            ),
            msg=values.MSG_GP_SEPARATE_SIGNOFF,
            abort_on_fail=False,
        )
        document = self.bloom.bloom_api_make(self.admin, "documents", project).body["id"]
        reader = self.bloom.bloom_api_scenario_user(
            self.admin, "maintainer", [project], "Requirements Author"
        )
        defect = self.bloom.bloom_api_make(self.admin, "defects", project).body["id"]
        design = self.bloom.bloom_api_make(self.admin, "designs", project).body["id"]
        author = self.bloom.bloom_api_scenario_user(
            self.admin, "maintainer", [project], "Design Author"
        )
        rejected = self.bloom.bloom_api_call(
            "PATCH", f"/api/defects/{defect}", author.headers, json={"status": "Rejected"}
        )
        self.assertEqual(
            (
                self.bloom.bloom_api_call(
                    "PATCH",
                    f"/api/documents/{document}",
                    reader.headers,
                    json={"status": "Approved"},
                ).status,
                (rejected.status, rejected.body["detail"]),
                self.bloom.bloom_api_call(
                    "PATCH", f"/api/designs/{design}", author.headers, json={"status": "Approved"}
                ).status,
            ),
            (
                values.STATUS_CONFLICT,
                (values.STATUS_FORBIDDEN, "Missing permission: approve on DEF."),
                values.STATUS_CONFLICT,
            ),
            msg=values.MSG_GP_OTHER_STATUSES,
            abort_on_fail=False,
        )

    def bud_controlled_creation_stays_draft_with_or_without_approve_422(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        author = self.bloom.bloom_api_scenario_user(
            self.admin, "maintainer", [project], "Requirements Author"
        )
        create = lambda who, status: self.bloom.bloom_api_make(
            who, "requirements", project, status=status
        )
        created = create(author.headers, "Draft")
        self.assertEqual(
            (created.status, created.body["status"]),
            (values.STATUS_CREATED, "Draft"),
            msg=values.MSG_GP_CREATED_DRAFT,
            abort_on_fail=False,
        )
        for who in (author.headers, self.admin):
            for status in ("Review", "Approved", "Rejected"):
                refused = create(who, status)
                self.assertEqual(
                    (refused.status, refused.body["detail"]),
                    (values.STATUS_UNPROCESSABLE, "New controlled documents start in Draft."),
                    msg=values.MSG_GP_CREATED_NOT_DRAFT.format(status=status),
                    abort_on_fail=False,
                )
        self.bloom.bloom_api_grant_scenario(self.admin, "Approver", author.id, project)
        rights = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/permissions", author.headers
        ).body["REQ"]
        reader = self.bloom.bloom_api_scenario_user(
            self.admin, "maintainer", [project], "Read Only"
        )
        by_reader = create(reader.headers, "Draft")
        self.assertEqual(
            (
                "approve" in rights,
                create(author.headers, "Approved").status,
                (by_reader.status, by_reader.body["detail"]),
            ),
            (
                True,
                values.STATUS_UNPROCESSABLE,
                (values.STATUS_FORBIDDEN, "Missing permission: create on REQ."),
            ),
            msg=values.MSG_GP_APPROVER_STILL_DRAFT,
            abort_on_fail=False,
        )

    def bud_a_sign_off_records_the_actor_of_the_assigned_handoff(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        requirement = self.bloom.bloom_api_make(
            self.admin, "requirements", project, req_origin="Customer"
        ).body["id"]
        hidden = self.bloom.bloom_api_make(self.admin, "requirements", project).body["id"]
        design = self.bloom.bloom_api_make(self.admin, "designs", project).body["id"]
        approver = self.bloom.bloom_api_scenario_user(
            self.admin, "maintainer", [project], "Approver"
        )
        author = self.bloom.bloom_api_scenario_user(
            self.admin, "maintainer", [project], "Requirements Author"
        )
        external = self.bloom.bloom_api_scenario_user(self.admin, "external", [project], "Approver")
        path = f"/api/artefacts/requirement/{requirement}"
        sign = lambda who, kind, item, signoff: self.bloom.bloom_api_call(
            "POST", f"/api/artefacts/{kind}/{item}/sign-off", who, json={"step": signoff}
        )
        unassigned = sign(approver.headers, "requirement", requirement, "review").status
        assigned = self.bloom.bloom_api_call(
            "PUT",
            path + "/workflow/assignees",
            self.admin,
            json={"reviewer_id": approver.id, "approver_id": approver.id},
        ).status
        requested = self.bloom.bloom_api_call(
            "POST", path + "/requests", self.admin, json={"kind": "review"}
        ).status
        missing_comment = sign(approver.headers, "requirement", requirement, "review").status
        by_author = sign(author.headers, "requirement", requirement, "review").status
        self.bloom.bloom_api_call(
            "POST", path + "/comments", approver.headers, json={"body": "Reviewed request content"}
        )
        reviewed = sign(approver.headers, "requirement", requirement, "review")
        self.assertEqual(
            (
                unassigned,
                assigned,
                requested,
                missing_comment,
                by_author,
                reviewed.status,
                reviewed.body["reviewed_by_id"],
            ),
            (
                values.STATUS_FORBIDDEN,
                values.STATUS_OK,
                values.STATUS_CREATED,
                values.STATUS_CONFLICT,
                values.STATUS_FORBIDDEN,
                values.STATUS_OK,
                approver.id,
            ),
            msg=values.MSG_GP_REVIEW_SIGNED,
            abort_on_fail=False,
        )
        refused = sign(external.headers, "requirement", requirement, "approve").status
        rights = set(
            self.bloom.bloom_api_call(
                "GET", f"/api/projects/{project}/permissions", external.headers
            ).body["REQ"]
        )
        approved = sign(approver.headers, "requirement", requirement, "approve")
        stored = self.bloom.bloom_api_call(
            "GET", f"/api/requirements/{requirement}", self.admin
        ).body
        on_design = sign(approver.headers, "design", design, "review")
        self.assertEqual(
            (
                refused,
                "review" in rights,
                rights & {"approve", "delete"},
                (approved.status, approved.body["approved_by_id"]),
                (stored["reviewed_by_id"], stored["approved_by_id"], stored["status"]),
                sign(external.headers, "requirement", hidden, "review").status,
                (on_design.status, on_design.body["detail"]),
                sign(approver.headers, "requirement", requirement, "sign").status,
            ),
            (
                values.STATUS_FORBIDDEN,
                True,
                set(),
                (values.STATUS_OK, approver.id),
                (approver.id, approver.id, "Approved"),
                values.STATUS_NOT_FOUND,
                (values.STATUS_FORBIDDEN, "Only the assigned reviewer requests approval."),
                values.STATUS_UNPROCESSABLE,
            ),
            msg=values.MSG_GP_APPROVAL_SIGNED,
            abort_on_fail=False,
        )

    def bud_import_statuses_cannot_skip_the_handoffs(self):
        values = self.parameters
        for grant_approve in (False, True):
            project = self.bloom.bloom_api_next_project(self.admin)["id"]
            existing = self.bloom.bloom_api_make(self.admin, "test-cases", project).body
            content = (
                "tc_id,title,status\n"
                f"{existing['tc_id']},Bypassed,Approved\n"
                ",Approved new,Approved\n"
                ",In review,Review\n"
                ",Draft new,Draft\n"
                f"{existing['tc_id']},Draft edit,Draft\n"
            ).encode()
            actions = ["view", "import", "create", "edit"] + (
                ["review", "approve"] if grant_approve else []
            )
            writer = self.bloom.bloom_api_permission_user(self.admin, {"TC": actions}, project)
            body = self.bloom.bloom_api_import_file(
                writer.headers,
                project,
                "test-cases",
                "c.csv",
                content,
                "application/octet-stream",
                format="csv",
            ).body
            stored = self.bloom.bloom_api_call(
                "GET", f"/api/test-cases/{existing['id']}", self.admin
            ).body
            rows = sorted(
                (row["title"], row["status"])
                for row in self.bloom.bloom_api_call(
                    "GET", "/api/test-cases", self.admin, params={"project_id": project}
                ).body["items"]
            )
            self.assertEqual(
                (
                    (body["created"], body["updated"], body["skipped"]),
                    body["errors"],
                    (stored["title"], stored["status"]),
                    rows,
                ),
                (
                    (1, 1, 3),
                    ["row 1: not permitted", "row 2: not permitted", "row 3: not permitted"],
                    ("Draft edit", "Draft"),
                    [("Draft edit", "Draft"), ("Draft new", "Draft")],
                ),
                msg=values.MSG_GP_IMPORT_STATUSES.format(with_approve=grant_approve),
                abort_on_fail=False,
            )

    def bud_case_and_suite_use_handoffs_while_a_campaign_keeps_its_rights(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        author = self.bloom.bloom_api_scenario_user(
            self.admin, "maintainer", [project], "Test Author"
        )
        signer = self.bloom.bloom_api_scenario_user(self.admin, "maintainer", [project], "Approver")
        case = self.bloom.bloom_api_make(author.headers, "test-cases", project).body["id"]
        suite = self.bloom.bloom_api_make(author.headers, "test-suites", project).body
        campaign = self.bloom.bloom_api_make(author.headers, "campaigns", project).body[
            "campaign_id"
        ]
        for slug, route, item, ref in (
            ("test-case", "test-cases", case, case),
            ("test-suite", "test-suites", suite["id"], suite["suite_id"]),
        ):
            refused = self.bloom.bloom_api_call(
                "PATCH", f"/api/{route}/{ref}", author.headers, json={"status": "Approved"}
            ).status
            path = f"/api/artefacts/{slug}/{item}"
            self.bloom.bloom_api_call(
                "PUT",
                path + "/workflow/assignees",
                self.admin,
                json={"reviewer_id": signer.id, "approver_id": signer.id},
            )
            self.bloom.bloom_api_call(
                "POST", path + "/requests", author.headers, json={"kind": "review"}
            )
            self.bloom.bloom_api_call(
                "POST", path + "/comments", signer.headers, json={"body": "Reviewed"}
            )
            self.bloom.bloom_api_call(
                "POST", path + "/requests", signer.headers, json={"kind": "approval"}
            )
            by_author = self.bloom.bloom_api_call(
                "POST", path + "/sign-off", author.headers, json={"step": "approve"}
            ).status
            approved = self.bloom.bloom_api_call(
                "POST", path + "/sign-off", signer.headers, json={"step": "approve"}
            ).status
            stored = self.bloom.bloom_api_call("GET", f"/api/{route}/{ref}", self.admin).body[
                "status"
            ]
            self.assertEqual(
                (refused, by_author, approved, stored),
                (values.STATUS_CONFLICT, values.STATUS_FORBIDDEN, values.STATUS_OK, "Approved"),
                msg=values.MSG_GP_HANDOFF_KIND.format(kind=slug),
                abort_on_fail=False,
            )
        path = f"/api/campaigns/{campaign}"
        moved = self.bloom.bloom_api_call(
            "PATCH", path, author.headers, json={"status": "In Progress"}
        ).status
        refused = self.bloom.bloom_api_call(
            "PATCH", path, author.headers, json={"status": "Approved"}
        )
        self.assertEqual(
            (moved, refused.status, refused.body["detail"]),
            (values.STATUS_OK, values.STATUS_FORBIDDEN, "Missing permission: approve on CMP."),
            msg=values.MSG_GP_CAMPAIGN_STATUS,
            abort_on_fail=False,
        )

    def bud_new_import_rows_start_draft_and_create_grants_no_edit(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        existing = self.bloom.bloom_api_make(self.admin, "test-cases", project).body
        creator = self.bloom.bloom_api_permission_user(
            self.admin, {"TC": ["view", "import", "create"]}, project
        )
        content = (
            "tc_id,title,status\n"
            f"{existing['tc_id']},No edit,Draft\n"
            ",Under review,Review\n"
            ",Signed,Approved\n"
            ",Draft new,Draft\n"
        ).encode()
        body = self.bloom.bloom_api_import_file(
            creator.headers,
            project,
            "test-cases",
            "c.csv",
            content,
            "application/octet-stream",
            format="csv",
        ).body
        stored = self.bloom.bloom_api_call(
            "GET", f"/api/test-cases/{existing['id']}", self.admin
        ).body
        rows = {
            (row["title"], row["status"])
            for row in self.bloom.bloom_api_call(
                "GET", "/api/test-cases", self.admin, params={"project_id": project}
            ).body["items"]
        }
        self.assertEqual(
            (
                (body["created"], body["updated"], body["skipped"]),
                body["errors"],
                (stored["title"], stored["status"]),
                rows,
            ),
            (
                (1, 0, 3),
                ["row 1: not permitted", "row 2: not permitted", "row 3: not permitted"],
                (existing["title"], "Draft"),
                {(existing["title"], "Draft"), ("Draft new", "Draft")},
            ),
            msg=values.MSG_GP_CREATE_NO_EDIT,
            abort_on_fail=False,
        )

    def bud_a_link_needs_both_ends_visible_and_an_external_users_own_ends(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        theirs = self.bloom.bloom_api_make(
            self.admin, "requirements", project, req_origin="Customer"
        ).body["id"]
        hidden = self.bloom.bloom_api_make(self.admin, "requirements", project).body["id"]
        design = self.bloom.bloom_api_make(
            self.admin, "designs", project, visibility="customer"
        ).body["id"]
        writes = ["view", "comment", "create", "edit", "delete"]
        user = self.bloom.bloom_api_permission_user(
            self.admin,
            {"REQ": writes, "TC": writes, "DES": ["view"], "link": writes},
            project,
            role="external",
            scope=["REQ", "TC"],
        )
        own_req = self.bloom.bloom_api_make(user.headers, "requirements", project).body["id"]
        own_case = self.bloom.bloom_api_make(user.headers, "test-cases", project).body["id"]
        link = lambda source, target, role="verifies": self.bloom.bloom_api_link_ends(
            user.headers, project, source, target, role
        )
        refused, unknown = link(("TC", own_case), ("REQ", theirs)), link(
            ("TC", own_case), ("REQ", hidden)
        )
        outside = link(("DES", design), ("REQ", own_req), "references")
        self.assertEqual(
            (
                link(("TC", own_case), ("REQ", own_req)).status,
                (refused.status, refused.body["detail"]),
                (unknown.status, unknown.body["detail"]),
                (outside.status, outside.body["detail"]),
            ),
            (
                values.STATUS_CREATED,
                (values.STATUS_FORBIDDEN, values.GP_ONLY_OWN),
                (values.STATUS_NOT_FOUND, "Target document not found in project"),
                (values.STATUS_NOT_FOUND, "Source document not found in project"),
            ),
            msg=values.MSG_GP_LINK_ENDS,
            abort_on_fail=False,
        )

    def bud_a_link_with_a_hidden_end_is_hidden_and_one_with_a_deleted_end_can_go(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        customer_case = self.bloom.bloom_api_make(
            self.admin, "test-cases", project, visibility="customer"
        ).body["id"]
        customer_req = self.bloom.bloom_api_make(
            self.admin, "requirements", project, req_origin="Customer"
        ).body["id"]
        hidden_req = self.bloom.bloom_api_make(self.admin, "requirements", project).body["id"]
        gone_req = self.bloom.bloom_api_make(self.admin, "requirements", project).body["id"]
        made = lambda target: self.bloom.bloom_api_link_ends(
            self.admin, project, ("TC", customer_case), ("REQ", target)
        ).body["id"]
        shown_link, hidden_link, orphan_link = made(customer_req), made(hidden_req), made(gone_req)
        self.bloom.bloom_api_call("DELETE", f"/api/requirements/{gone_req}", self.admin)
        external = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "Test Author", "Requirements Author"
        )
        maintainer = self.bloom.bloom_api_scenario_user(
            self.admin, "maintainer", [project], "Test Author"
        )
        self.assertEqual(
            (
                self.bloom.bloom_api_call(
                    "DELETE", f"/api/links/{shown_link}", external.headers
                ).status,
                self.bloom.bloom_api_call(
                    "DELETE", f"/api/links/{hidden_link}", external.headers
                ).status,
                self.bloom.bloom_api_call(
                    "DELETE", f"/api/links/{orphan_link}", maintainer.headers
                ).status,
            ),
            (values.STATUS_FORBIDDEN, values.STATUS_NOT_FOUND, values.STATUS_NO_CONTENT),
            msg=values.MSG_GP_LINK_DELETE,
            abort_on_fail=False,
        )

    def bud_a_tag_links_only_a_visible_artefact_of_the_same_project(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        other = self.bloom.bloom_api_next_project(self.admin)["id"]
        shown = self.bloom.bloom_api_make(
            self.admin, "requirements", project, req_origin="Customer"
        ).body["id"]
        hidden = self.bloom.bloom_api_make(self.admin, "requirements", project).body["id"]
        elsewhere = self.bloom.bloom_api_make(self.admin, "requirements", other).body["id"]
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "Requirements Author"
        )
        tags = [
            {
                "type": "mention",
                "attrs": {"id": f"REQ:{item}", "label": "x", "mentionSuggestionChar": "#"},
            }
            for item in (shown, hidden, elsewhere, 999999)
        ]
        body = {"type": "doc", "content": [{"type": "paragraph", "content": tags}]}
        created = self.bloom.bloom_api_make(
            user.headers, "requirements", project, content_json=body
        )
        links = self.bloom.bloom_api_call(
            "GET",
            "/api/links",
            self.admin,
            params={"project_id": project, "source_type": "REQ", "source_id": created.body["id"]},
        ).body
        self.assertEqual(
            (created.status, [(link["target_type"], link["target_id"]) for link in links]),
            (values.STATUS_CREATED, [("REQ", shown)]),
            msg=values.MSG_GP_TAG_VISIBLE,
            abort_on_fail=False,
        )

    def bud_an_external_import_links_only_rows_the_importer_created(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        theirs = self.bloom.bloom_api_make(
            self.admin, "requirements", project, req_origin="Customer"
        ).body["req_id"]
        user = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "Test Author", "Requirements Author"
        )
        export = (
            "<suite><sections><section><name>Rail</name><cases><case><id>C7</id>"
            f"<title>Linked</title><references>{theirs}</references>"
            "</case></cases></section></sections></suite>"
        ).encode()
        railed = self.bloom.bloom_api_import_file(
            user.headers,
            project,
            "testrail",
            "t.xml",
            export,
            "application/octet-stream",
            format="xml",
        ).body
        unrelated = re.sub(
            rb'<SPEC-RELATION IDENTIFIER="REL-1">.*?</SPEC-RELATION>',
            b"",
            values.GP_REQIF,
            flags=re.S,
        )
        imported = self.bloom.bloom_api_import_file(
            self.admin, project, "reqif", "s.reqif", unrelated, "application/octet-stream"
        ).body
        for item in self.bloom.bloom_api_call(
            "GET", "/api/requirements", self.admin, params={"project_id": project}
        ).body["items"]:
            self.bloom.bloom_api_call(
                "PATCH",
                f"/api/requirements/{item['id']}",
                self.admin,
                json={"req_origin": "Customer"},
            )
        again = self.bloom.bloom_api_import_file(
            user.headers, project, "reqif", "s.reqif", values.GP_REQIF, "application/octet-stream"
        ).body
        self.assertEqual(
            (
                (railed["links_created"], railed["errors"]),
                imported["links_created"],
                (again["links_created"], again["errors"]),
            ),
            ((0, ["case C7: links not permitted"]), 0, (0, ["relation REL-1: not permitted"])),
            msg=values.MSG_GP_IMPORT_LINKS,
            abort_on_fail=False,
        )

    def bud_a_hidden_link_is_not_found_before_a_missing_delete_right(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        case = self.bloom.bloom_api_make(
            self.admin, "test-cases", project, visibility="customer"
        ).body["id"]
        shown = self.bloom.bloom_api_make(
            self.admin, "requirements", project, req_origin="Customer"
        ).body["id"]
        hidden = self.bloom.bloom_api_make(self.admin, "requirements", project).body["id"]
        shown_link = self.bloom.bloom_api_link_ends(
            self.admin, project, ("TC", case), ("REQ", shown)
        ).body["id"]
        hidden_link = self.bloom.bloom_api_link_ends(
            self.admin, project, ("TC", case), ("REQ", hidden)
        ).body["id"]
        reader = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "External Reader"
        )
        refused = self.bloom.bloom_api_call("DELETE", f"/api/links/{shown_link}", reader.headers)
        self.assertEqual(
            (
                self.bloom.bloom_api_call(
                    "DELETE", f"/api/links/{hidden_link}", reader.headers
                ).status,
                (refused.status, refused.body["detail"]),
            ),
            (
                values.STATUS_NOT_FOUND,
                (values.STATUS_FORBIDDEN, "Missing permission: delete on link."),
            ),
            msg=values.MSG_GP_HIDDEN_LINK_FIRST,
            abort_on_fail=False,
        )

    def bud_a_read_by_id_needs_the_view_right(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        requirement = self.bloom.bloom_api_make(self.admin, "requirements", project).body["id"]
        blind = self.bloom.bloom_api_permission_user(self.admin, {"REQ": ["comment"]}, project)
        seeing = self.bloom.bloom_api_permission_user(self.admin, {"REQ": ["view"]}, project)
        for path in (
            f"/api/requirements/{requirement}",
            f"/api/requirements/{requirement}/test-runs",
            f"/api/artefacts/requirement/{requirement}/comments",
            f"/api/artefacts/requirement/{requirement}/activity",
            f"/api/artefacts/requirement/{requirement}/related",
        ):
            self.assertEqual(
                (
                    self.bloom.bloom_api_call("GET", path, blind.headers).status,
                    self.bloom.bloom_api_call("GET", path, seeing.headers).status,
                ),
                (values.STATUS_NOT_FOUND, values.STATUS_OK),
                msg=values.MSG_GP_VIEW_BY_ID.format(path=path),
                abort_on_fail=False,
            )

    def bud_commenting_needs_review_visibility_and_assignment(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        requirement = self.bloom.bloom_api_make(
            self.admin, "requirements", project, req_origin="Customer"
        ).body["id"]
        reader = self.bloom.bloom_api_scenario_user(
            self.admin, "maintainer", [project], "Read Only"
        )
        external = self.bloom.bloom_api_scenario_user(
            self.admin, "external", [project], "External Reader"
        )
        path = f"/api/artefacts/requirement/{requirement}"
        for who in (reader, external):
            refused = self.bloom.bloom_api_call(
                "POST", path + "/comments", who.headers, json={"body": "Read only"}
            )
            self.assertEqual(
                (refused.status, refused.body["detail"]),
                (
                    values.STATUS_FORBIDDEN,
                    "Only the document's creator, assignee, reviewer or approver may comment.",
                ),
                msg=values.MSG_GP_COMMENT_READERS,
                abort_on_fail=False,
            )
        reviewer = self.bloom.bloom_api_permission_user(
            self.admin, {"REQ": ["review"]}, project, role="external", scope=["REQ"]
        )
        blind = self.bloom.bloom_api_call(
            "GET", f"/api/requirements/{requirement}", reviewer.headers
        ).status
        invalid = self.bloom.bloom_api_call(
            "PUT", path + "/workflow/assignees", self.admin, json={"reviewer_id": reviewer.id}
        ).status
        self.bloom.bloom_api_grant_scenario(self.admin, "External Reader", reviewer.id, project)
        seeing = self.bloom.bloom_api_call(
            "GET", f"/api/requirements/{requirement}", reviewer.headers
        ).status
        unassigned = self.bloom.bloom_api_call(
            "POST", path + "/comments", reviewer.headers, json={"body": "Not assigned"}
        ).status
        assigned = self.bloom.bloom_api_call(
            "PUT", path + "/workflow/assignees", self.admin, json={"reviewer_id": reviewer.id}
        ).status
        comment = self.bloom.bloom_api_call(
            "POST", path + "/comments", reviewer.headers, json={"body": "Assigned customer review"}
        )
        rights = set(
            self.bloom.bloom_api_call(
                "GET", f"/api/projects/{project}/permissions", reviewer.headers
            ).body["REQ"]
        )
        self.assertEqual(
            (
                blind,
                invalid,
                seeing,
                unassigned,
                assigned,
                comment.status,
                comment.body["author_user_id"],
                {"view", "review"} <= rights,
                rights & {"create", "edit", "approve", "delete"},
            ),
            (
                values.STATUS_NOT_FOUND,
                values.STATUS_UNPROCESSABLE,
                values.STATUS_OK,
                values.STATUS_FORBIDDEN,
                values.STATUS_OK,
                values.STATUS_CREATED,
                reviewer.id,
                True,
                set(),
            ),
            msg=values.MSG_GP_COMMENT_REVIEWER,
            abort_on_fail=False,
        )

    def bud_a_reviewer_or_approver_must_see_and_hold_the_right_422(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        approver = self.bloom.bloom_api_scenario_user(
            self.admin, "maintainer", [project], "Approver"
        )
        author = self.bloom.bloom_api_scenario_user(
            self.admin, "maintainer", [project], "Requirements Author"
        )
        outsider = self.bloom.bloom_api_new_member(
            self.admin, self.bloom.bloom_api_next_name("outsider").replace(" ", "-")
        )
        external = self.bloom.bloom_api_scenario_user(self.admin, "external", [project], "Approver")
        create = lambda kind, **assignees: self.bloom.bloom_api_make(
            self.admin, kind, project, **assignees
        )
        self.assertEqual(
            create("requirements", reviewer_id=approver.id).status,
            values.STATUS_CREATED,
            msg=values.MSG_GP_ASSIGN_APPROVER,
            abort_on_fail=False,
        )
        for who in (author, outsider, external):
            refused = create("requirements", reviewer_id=who.id)
            self.assertEqual(
                (refused.status, "cannot see" in refused.body["detail"]),
                (values.STATUS_UNPROCESSABLE, True),
                msg=values.MSG_GP_ASSIGN_REFUSED,
                abort_on_fail=False,
            )
        requirement = create("requirements").body["id"]
        self.assertEqual(
            (
                create("test-cases", approver_id=external.id).status,
                create("defects", reviewer_id=external.id).status,
                self.bloom.bloom_api_call(
                    "PATCH",
                    f"/api/requirements/{requirement}",
                    self.admin,
                    json={"approver_id": author.id},
                ).status,
            ),
            (values.STATUS_UNPROCESSABLE,) * 3,
            msg=values.MSG_GP_ASSIGN_OTHER_KINDS,
            abort_on_fail=False,
        )

    def bud_what_a_user_cannot_view_they_cannot_change_404(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        requirement = self.bloom.bloom_api_make(self.admin, "requirements", project).body["id"]
        case = self.bloom.bloom_api_make(self.admin, "test-cases", project).body["id"]
        writes = ["create", "edit", "delete", "comment"]
        blind = self.bloom.bloom_api_permission_user(
            self.admin,
            {"REQ": writes, "TC": ["view", *writes], "link": ["view", "create"]},
            project,
            scope=["TC"],
        )
        self.assertEqual(
            (
                self.bloom.bloom_api_call(
                    "PATCH", f"/api/requirements/{requirement}", blind.headers, json={"title": "x"}
                ).status,
                self.bloom.bloom_api_call(
                    "POST",
                    f"/api/artefacts/requirement/{requirement}/comments",
                    blind.headers,
                    json={"body": "x"},
                ).status,
                self.bloom.bloom_api_link_ends(
                    blind.headers, project, ("TC", case), ("REQ", requirement)
                ).status,
                self.bloom.bloom_api_call(
                    "DELETE", f"/api/requirements/{requirement}", blind.headers
                ).status,
            ),
            (values.STATUS_NOT_FOUND,) * 4,
            msg=values.MSG_GP_UNSEEN_CHANGES,
            abort_on_fail=False,
        )

    def bud_a_list_of_a_type_without_view_is_empty(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        for kind in values.GP_LIST_KINDS:
            self.bloom.bloom_api_make(self.admin, kind, project)
        blind = self.bloom.bloom_api_permission_user(self.admin, {"link": ["view"]}, project)
        seeing = self.bloom.bloom_api_permission_user(
            self.admin, {code: ["view"] for code, _ in values.GP_LIST_KINDS.values()}, project
        )
        rows = lambda body: body["items"] if isinstance(body, dict) else body
        for kind in values.GP_LIST_KINDS:
            hidden = self.bloom.bloom_api_call(
                "GET", f"/api/{kind}", blind.headers, params={"project_id": project}
            )
            shown = self.bloom.bloom_api_call(
                "GET", f"/api/{kind}", seeing.headers, params={"project_id": project}
            )
            self.assertEqual(
                (hidden.status, rows(hidden.body), len(rows(shown.body))),
                (values.STATUS_OK, [], 1),
                msg=values.MSG_GP_LIST_VIEW.format(kind=kind),
                abort_on_fail=False,
            )

    def bud_the_registry_and_type_summary_leave_out_a_type_without_view(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        requirement = self.bloom.bloom_api_make(self.admin, "requirements", project).body
        case = self.bloom.bloom_api_make(self.admin, "test-cases", project).body["id"]
        self.bloom.bloom_api_link_ends(
            self.admin, project, ("TC", case), ("REQ", requirement["id"])
        )
        self.bloom.bloom_api_make(self.admin, "campaigns", project, test_case_ids=[case])
        reader = self.bloom.bloom_api_permission_user(
            self.admin, {"REQ": ["view"], "CMP": ["view"]}, project
        )
        docs = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/docs", reader.headers
        ).body["items"]
        summary = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/doc-type-summary", reader.headers
        ).body
        detail_path = f"/api/projects/{project}/docs/requirements/{requirement['req_id']}"
        hidden = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/next-doc-id/TC", reader.headers
        )
        unknown = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/next-doc-id/XYZ", reader.headers
        )
        self.assertEqual(
            (
                sorted(doc["doc_type"] for doc in docs),
                all(doc["incoming_links"] == doc["outgoing_links"] == 0 for doc in docs),
                sorted(entry["doc_type"] for entry in summary["types"]),
                summary["membership_edges"],
                self.bloom.bloom_api_call("GET", detail_path, reader.headers).body[
                    "incoming_links"
                ],
                self.bloom.bloom_api_call("GET", detail_path, self.admin).body["incoming_links"],
                (hidden.status, unknown.status, hidden.body["detail"]),
            ),
            (
                ["CMP", "REQ"],
                True,
                ["CMP", "REQ"],
                [],
                0,
                1,
                (
                    values.STATUS_BAD_REQUEST,
                    values.STATUS_BAD_REQUEST,
                    "Unsupported document type: TC",
                ),
            ),
            msg=values.MSG_GP_REGISTRY_VIEW,
            abort_on_fail=False,
        )

    def bud_the_link_list_leaves_out_links_to_a_type_without_view(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        requirement = self.bloom.bloom_api_make(self.admin, "requirements", project).body["id"]
        case = self.bloom.bloom_api_make(self.admin, "test-cases", project).body["id"]
        self.bloom.bloom_api_link_ends(self.admin, project, ("TC", case), ("REQ", requirement))
        partial = self.bloom.bloom_api_permission_user(
            self.admin, {"REQ": ["view"], "link": ["view"]}, project
        )
        both = self.bloom.bloom_api_permission_user(
            self.admin, {"REQ": ["view"], "TC": ["view"], "link": ["view"]}, project
        )
        query = {"project_id": project}
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", "/api/links", partial.headers, params=query).body,
                len(
                    self.bloom.bloom_api_call("GET", "/api/links", both.headers, params=query).body
                ),
            ),
            ([], 1),
            msg=values.MSG_GP_LINK_LIST_VIEW,
            abort_on_fail=False,
        )

    def bud_nested_rows_and_counts_follow_the_view_right(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        requirement = self.bloom.bloom_api_make(self.admin, "requirements", project).body["id"]
        case = self.bloom.bloom_api_make(self.admin, "test-cases", project).body["id"]
        self.bloom.bloom_api_link_ends(self.admin, project, ("TC", case), ("REQ", requirement))
        campaign = self.bloom.bloom_api_make(
            self.admin, "campaigns", project, test_case_ids=[case]
        ).body["campaign_id"]
        reader = self.bloom.bloom_api_permission_user(
            self.admin, {"REQ": ["view"], "CMP": ["view"]}, project
        )
        detail = self.bloom.bloom_api_call(
            "GET", f"/api/requirements/{requirement}", reader.headers
        ).body
        row = self.bloom.bloom_api_call(
            "GET", "/api/requirements", reader.headers, params={"project_id": project}
        ).body["items"][0]
        campaign_detail = self.bloom.bloom_api_call(
            "GET", f"/api/campaigns/{campaign}", reader.headers
        ).body
        self.assertEqual(
            (
                detail["linked_test_cases"],
                detail["test_case_count"],
                row["test_case_count"],
                campaign_detail["items"],
                campaign_detail["total_items"],
                self.bloom.bloom_api_call("GET", f"/api/campaigns/{campaign}", self.admin).body[
                    "total_items"
                ],
            ),
            ([], 0, 0, [], 0, 1),
            msg=values.MSG_GP_NESTED_VIEW,
            abort_on_fail=False,
        )

    def bud_search_dashboard_and_counts_leave_out_a_type_without_view(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        word = self.bloom.bloom_api_next_name("needle").replace(" ", "")
        self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            self.admin,
            json={
                "project_id": project,
                "title": word,
                "visibility": "customer",
                "req_origin": "Customer",
            },
        )
        self.bloom.bloom_api_call(
            "POST",
            "/api/test-cases",
            self.admin,
            json={"project_id": project, "title": word, "visibility": "customer"},
        )
        reader = self.bloom.bloom_api_permission_user(self.admin, {"REQ": ["view"]}, project)
        external = self.bloom.bloom_api_new_member(
            self.admin,
            self.bloom.bloom_api_next_name("external-counted").replace(" ", "-"),
            "external",
        )
        policy = self.bloom.bloom_api_new_policy(
            self.admin,
            self.bloom.bloom_api_next_name("Counted reader"),
            {"*": ["view", "comment"]},
            "customer",
            ["REQ"],
        )
        self.bloom.bloom_api_admit(self.admin, project, external.id, policy_ids=[policy["id"]])
        self.bloom.bloom_clear_dashboard_cache()
        counts = self.bloom.bloom_api_call("GET", f"/api/projects/{project}", reader.headers).body
        found = self.bloom.bloom_api_call(
            "GET", "/api/search", external.headers, params={"q": word, "project_id": project}
        ).body
        stats = self.bloom.bloom_api_call("GET", "/api/dashboard/stats", external.headers).body
        self.assertEqual(
            (
                (counts["requirement_count"], counts["test_case_count"]),
                [item["type"] for item in found["items"]],
                (stats["total_requirements"], stats["total_test_cases"]),
            ),
            ((1, 0), ["REQ"], (1, 0)),
            msg=values.MSG_GP_COUNTS_VIEW,
            abort_on_fail=False,
        )

    def bud_traceability_follows_the_view_right(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        requirement = self.bloom.bloom_api_make(self.admin, "requirements", project).body["id"]
        case = self.bloom.bloom_api_make(self.admin, "test-cases", project).body["id"]
        self.bloom.bloom_api_link_ends(self.admin, project, ("TC", case), ("REQ", requirement))
        no_requirements = self.bloom.bloom_api_permission_user(
            self.admin, {"TC": ["view"]}, project
        )
        no_test_cases = self.bloom.bloom_api_permission_user(self.admin, {"REQ": ["view"]}, project)
        query = {"project_id": project}
        self.assertEqual(
            (
                self.bloom.bloom_api_call(
                    "GET", "/api/traceability", no_requirements.headers, params=query
                ).body["items"],
                self.bloom.bloom_api_call(
                    "GET", f"/api/traceability/coverage-gaps/{project}", no_requirements.headers
                ).body["total_requirements"],
                self.bloom.bloom_api_call(
                    "GET", f"/api/traceability/impact/{requirement}", no_requirements.headers
                ).status,
                [
                    item["linked_test_cases"]
                    for item in self.bloom.bloom_api_call(
                        "GET", "/api/traceability", no_test_cases.headers, params=query
                    ).body["items"]
                ],
                self.bloom.bloom_api_call(
                    "GET", f"/api/traceability/impact/{requirement}", no_test_cases.headers
                ).body["root_requirement"]["test_case_count"],
            ),
            ([], 0, values.STATUS_NOT_FOUND, [[]], 0),
            msg=values.MSG_GP_TRACE_VIEW,
            abort_on_fail=False,
        )

    def bud_an_export_leaves_out_types_without_view(self):
        values = self.parameters
        project = self.bloom.bloom_api_next_project(self.admin)["id"]
        requirement = self.bloom.bloom_api_make(self.admin, "requirements", project).body["id"]
        case = self.bloom.bloom_api_make(self.admin, "test-cases", project).body
        self.bloom.bloom_api_link_ends(
            self.admin, project, ("TC", case["id"]), ("REQ", requirement)
        )
        exporter = self.bloom.bloom_api_permission_user(
            self.admin, {"REQ": ["view", "export"], "TC": ["export"]}, project
        )
        cases = self.bloom.bloom_api_raw(
            "GET", f"/api/projects/{project}/export/test-cases", exporter.headers
        )
        trace = self.bloom.bloom_api_raw(
            "GET", f"/api/projects/{project}/export/traceability", exporter.headers
        )
        self.assertEqual(
            (
                cases.status,
                cases.text.strip().count("\n"),
                trace.status,
                case["tc_id"] in trace.text,
            ),
            (values.STATUS_OK, 0, values.STATUS_OK, False),
            msg=values.MSG_GP_EXPORT_VIEW,
            abort_on_fail=False,
        )
