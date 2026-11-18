"""
* @file     ${tests/api/tags_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the tag base, the tags of an artefact and the tags a policy ticks.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the tags over HTTP.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class TagsHttpBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_administrators_manage_the_tag_base(self):
        values = self.parameters
        made = self.bloom.bloom_api_new_tag(self.admin, "base-tag")
        renamed = self.bloom.bloom_api_call(
            "PATCH", f"/api/tags/{made['id']}", self.admin, json={"name": "base-tag-x"}
        )
        clash = self.bloom.bloom_api_call(
            "POST", "/api/tags", self.admin, json={"name": "base-tag-x"}
        )
        self.assertEqual(
            (renamed.status, renamed.body["name"], clash.status),
            (values.STATUS_OK, "base-tag-x", values.STATUS_CONFLICT),
            msg=values.MSG_TAGH_RENAMED,
            abort_on_fail=False,
        )
        user = self.bloom.bloom_api_new_member(self.admin, "tag-maintainer")
        unknown = self.bloom.bloom_api_call(
            "POST",
            "/api/policies",
            self.admin,
            json={"name": "Unknown tag policy", "rules": {"REQ": {"read": True, "tags": [999999]}}},
        )
        self.assertEqual(
            (
                self.bloom.bloom_api_call(
                    "POST", "/api/tags", user.headers, json={"name": "x"}
                ).status,
                unknown.status,
            ),
            (values.STATUS_FORBIDDEN, values.STATUS_BAD_REQUEST),
            msg=values.MSG_TAGH_ADMIN_ONLY,
            abort_on_fail=False,
        )

    def bud_an_external_reader_sees_only_their_tag(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TAG_HTTP_PREFIXES[0])["id"]
        mine, other = (
            self.bloom.bloom_api_new_tag(self.admin, "ext-mine")["id"],
            self.bloom.bloom_api_new_tag(self.admin, "ext-other")["id"],
        )
        shown, hidden, untagged = (
            self.bloom.bloom_api_call(
                "POST",
                "/api/requirements",
                self.admin,
                json={"project_id": project, "title": "Shown", "req_origin": "Customer"},
            ).body["id"],
            self.bloom.bloom_api_call(
                "POST",
                "/api/requirements",
                self.admin,
                json={"project_id": project, "title": "Hidden", "req_origin": "Customer"},
            ).body["id"],
            self.bloom.bloom_api_call(
                "POST",
                "/api/requirements",
                self.admin,
                json={"project_id": project, "title": "Untagged", "req_origin": "Customer"},
            ).body["id"],
        )
        self.bloom.bloom_api_tag(self.admin, "requirement", shown, [mine])
        self.bloom.bloom_api_tag(self.admin, "requirement", hidden, [other])
        reader = self.bloom.bloom_api_ruled_member(
            self.admin, "tag-reader", project, "external", {"REQ": {"read": True, "tags": [mine]}}
        ).headers
        self.assertEqual(
            [
                row["id"]
                for row in self.bloom.bloom_api_call(
                    "GET", "/api/requirements", reader, params={"project_id": project}
                ).body["items"]
            ],
            [shown],
            msg=values.MSG_TAGH_EXTERNAL_LIST,
            abort_on_fail=False,
        )
        self.assertEqual(
            [
                self.bloom.bloom_api_call("GET", f"/api/requirements/{row}", reader).status
                for row in (hidden, untagged)
            ],
            [values.STATUS_NOT_FOUND] * 2,
            msg=values.MSG_TAGH_EXTERNAL_HIDDEN,
            abort_on_fail=False,
        )
        offered = [
            t["id"]
            for t in self.bloom.bloom_api_call(
                "GET", "/api/tags", reader, params={"project_id": project}
            ).body
        ]
        self.assertEqual(
            (
                self.bloom.bloom_api_tags_of(reader, "requirement", shown),
                offered,
                self.bloom.bloom_api_tag(reader, "requirement", shown, [mine]).status,
            ),
            ([mine], [mine], values.STATUS_FORBIDDEN),
            msg=values.MSG_TAGH_EXTERNAL_TAGS,
            abort_on_fail=False,
        )

    def bud_an_editor_changes_only_the_tags_they_tick(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TAG_HTTP_PREFIXES[1])["id"]
        mine, also_mine, other = (
            self.bloom.bloom_api_new_tag(self.admin, "edit-mine")["id"],
            self.bloom.bloom_api_new_tag(self.admin, "edit-also")["id"],
            self.bloom.bloom_api_new_tag(self.admin, "edit-other")["id"],
        )
        row = self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            self.admin,
            json={"project_id": project, "title": "Scoped", "req_origin": "Internal"},
        ).body["id"]
        self.bloom.bloom_api_tag(self.admin, "requirement", row, [mine, other])
        editor = self.bloom.bloom_api_ruled_member(
            self.admin,
            "tag-editor",
            project,
            "maintainer",
            {"REQ": {"read": True, "write": True, "tags": [mine, also_mine]}},
        ).headers
        added = self.bloom.bloom_api_tag(editor, "requirement", row, [mine, also_mine])
        self.assertEqual(
            (added.status, sorted(t["id"] for t in added.body)),
            (values.STATUS_OK, sorted([mine, also_mine])),
            msg=values.MSG_TAGH_EDITOR_ADDED,
            abort_on_fail=False,
        )
        foreign = self.bloom.bloom_api_new_tag(self.admin, "edit-foreign")["id"]
        outside = self.bloom.bloom_api_tag(editor, "requirement", row, [mine, foreign])
        emptied = self.bloom.bloom_api_tag(editor, "requirement", row, [])
        self.assertEqual(
            ((outside.status, outside.body["detail"]), (emptied.status, emptied.body["detail"])),
            (
                (values.STATUS_FORBIDDEN, values.TAG_HTTP_OUTSIDE),
                (values.STATUS_FORBIDDEN, values.TAG_HTTP_INSIDE),
            ),
            msg=values.MSG_TAGH_EDITOR_REFUSED,
            abort_on_fail=False,
        )
        narrowed = self.bloom.bloom_api_tag(editor, "requirement", row, [also_mine])
        self.assertEqual(
            (
                [t["id"] for t in narrowed.body],
                sorted(self.bloom.bloom_api_tags_of(self.admin, "requirement", row)),
            ),
            ([also_mine], sorted([also_mine, other])),
            msg=values.MSG_TAGH_EDITOR_NARROWED,
            abort_on_fail=False,
        )

    def bud_a_customer_policy_shows_customer_requirements_only(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TAG_HTTP_PREFIXES[2])["id"]
        shown, hidden = (
            self.bloom.bloom_api_call(
                "POST",
                "/api/requirements",
                self.admin,
                json={"project_id": project, "title": "Customer row", "req_origin": "Customer"},
            ).body["id"],
            self.bloom.bloom_api_call(
                "POST",
                "/api/requirements",
                self.admin,
                json={"project_id": project, "title": "Internal row", "req_origin": "Internal"},
            ).body["id"],
        )
        reader = self.bloom.bloom_api_ruled_member(
            self.admin,
            "customer-ticker",
            project,
            "maintainer",
            {"REQ": {"read": True, "visibility": ["customer"]}},
        ).headers
        self.assertEqual(
            (
                [
                    row["id"]
                    for row in self.bloom.bloom_api_call(
                        "GET", "/api/requirements", reader, params={"project_id": project}
                    ).body["items"]
                ],
                self.bloom.bloom_api_call("GET", f"/api/requirements/{hidden}", reader).status,
            ),
            ([shown], values.STATUS_NOT_FOUND),
            msg=values.MSG_TAGH_CUSTOMER,
            abort_on_fail=False,
        )

    def bud_a_scoped_user_creates_with_one_of_their_tags(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TAG_HTTP_PREFIXES[3])["id"]
        first, second, foreign = (
            self.bloom.bloom_api_new_tag(self.admin, "create-first")["id"],
            self.bloom.bloom_api_new_tag(self.admin, "create-second")["id"],
            self.bloom.bloom_api_new_tag(self.admin, "create-foreign")["id"],
        )
        user = self.bloom.bloom_api_ruled_member(
            self.admin,
            "scoped-creator",
            project,
            "maintainer",
            {"REQ": {"read": True, "write": True, "tags": [first, second]}},
        ).headers
        create = lambda title, tag_ids: self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            user,
            json={"project_id": project, "title": title, "tag_ids": tag_ids},
        )
        missing, outside = create("No tag", []), create("Foreign tag", [first, foreign])
        self.assertEqual(
            ((missing.status, missing.body["detail"]), (outside.status, outside.body["detail"])),
            (
                (values.STATUS_FORBIDDEN, values.TAG_HTTP_NO_CREATE),
                (values.STATUS_FORBIDDEN, values.TAG_HTTP_GIVEN),
            ),
            msg=values.MSG_TAGH_CREATE_REFUSED,
            abort_on_fail=False,
        )
        made = create("Own tag", [second])
        self.assertEqual(
            (
                made.status,
                [
                    row["id"]
                    for row in self.bloom.bloom_api_call(
                        "GET", "/api/requirements", user, params={"project_id": project}
                    ).body["items"]
                ],
                self.bloom.bloom_api_tags_of(self.admin, "requirement", made.body["id"]),
            ),
            (values.STATUS_CREATED, [made.body["id"]], [second]),
            msg=values.MSG_TAGH_CREATED,
            abort_on_fail=False,
        )

    def bud_an_unscoped_user_gives_any_tag_or_none(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TAG_HTTP_PREFIXES[4])["id"]
        free = self.bloom.bloom_api_new_tag(self.admin, "free-tag")["id"]
        for what, tag_ids in (("no tag", []), ("a tag", [free])):
            made = self.bloom.bloom_api_call(
                "POST",
                "/api/requirements",
                self.admin,
                json={"project_id": project, "title": what, "tag_ids": tag_ids},
            )
            self.assertEqual(
                (
                    made.status,
                    self.bloom.bloom_api_tags_of(self.admin, "requirement", made.body["id"]),
                ),
                (values.STATUS_CREATED, tag_ids),
                msg=values.MSG_TAGH_FREE.format(what=what),
                abort_on_fail=False,
            )
        unknown = self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            self.admin,
            json={"project_id": project, "title": "Unknown", "tag_ids": [999999]},
        )
        self.assertEqual(
            unknown.status,
            values.STATUS_BAD_REQUEST,
            msg=values.MSG_TAGH_UNKNOWN,
            abort_on_fail=False,
        )

    def bud_the_create_form_learns_the_tag_scope(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TAG_HTTP_PREFIXES[5])["id"]
        mine, other = (
            self.bloom.bloom_api_new_tag(self.admin, "scope-mine")["id"],
            self.bloom.bloom_api_new_tag(self.admin, "scope-other")["id"],
        )
        user = self.bloom.bloom_api_ruled_member(
            self.admin,
            "scope-learner",
            project,
            "maintainer",
            {"REQ": {"read": True, "write": True, "tags": [mine]}},
        ).headers
        limited = self.bloom.bloom_api_call(
            "GET", "/api/tags/scope", user, params={"project_id": project}
        ).body
        free = self.bloom.bloom_api_call(
            "GET", "/api/tags/scope", self.admin, params={"project_id": project}
        ).body
        self.assertEqual(
            (
                limited["limited"],
                [t["id"] for t in limited["tags"]],
                free["limited"],
                {mine, other} <= {t["id"] for t in free["tags"]},
            ),
            (True, [mine], False, True),
            msg=values.MSG_TAGH_SCOPE,
            abort_on_fail=False,
        )

    def bud_an_import_by_a_scoped_user_needs_one_of_their_tags(self):
        values = self.parameters
        self.bloom.bloom_limit_reqif_imports(100)
        project = self.bloom.bloom_api_new_project(self.admin, values.TAG_HTTP_PREFIXES[6])["id"]
        first, second = (
            self.bloom.bloom_api_new_tag(self.admin, "import-first")["id"],
            self.bloom.bloom_api_new_tag(self.admin, "import-second")["id"],
        )
        rules = {
            "TC": {"read": True, "write": True, "tags": [first, second]},
            "TS": {"read": True, "write": True, "tags": [first, second]},
        }
        user = self.bloom.bloom_api_ruled_member(
            self.admin, "scoped-importer", project, "maintainer", rules
        ).headers
        run = lambda **params: self.bloom.bloom_api_import_file(
            user,
            project,
            "testrail",
            "t.xml",
            values.TAG_HTTP_TESTRAIL,
            "application/xml",
            format="xml",
            **params,
        )
        refused = run()
        self.assertEqual(
            (refused.status, refused.body["created"], refused.body["errors"]),
            (values.STATUS_CREATED, 0, ["case C1: not permitted"]),
            msg=values.MSG_TAGH_IMPORT_REFUSED,
            abort_on_fail=False,
        )
        made = run(tag_ids=[second])
        cases = self.bloom.bloom_api_call(
            "GET", "/api/test-cases", user, params={"project_id": project}
        ).body["items"]
        self.assertEqual(
            (
                made.status,
                len(cases),
                (
                    self.bloom.bloom_api_tags_of(self.admin, "test-case", cases[0]["id"])
                    if cases
                    else None
                ),
            ),
            (values.STATUS_CREATED, 1, [second]),
            msg=values.MSG_TAGH_IMPORTED,
            abort_on_fail=False,
        )

    def bud_a_visibility_change_needs_a_write_policy_ticking_it(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TAG_HTTP_PREFIXES[7])["id"]
        row = self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            self.admin,
            json={"project_id": project, "title": "Retag", "req_origin": "Internal"},
        ).body["id"]
        narrow = self.bloom.bloom_api_ruled_member(
            self.admin,
            "narrow-retagger",
            project,
            "maintainer",
            {"REQ": {"read": True, "write": True, "visibility": ["internal"]}},
            {"REQ": {"read": True, "visibility": ["customer"]}},
        ).headers
        refused = self.bloom.bloom_api_call(
            "PATCH", f"/api/requirements/{row}", narrow, json={"req_origin": "Customer"}
        )
        wide = self.bloom.bloom_api_ruled_member(
            self.admin,
            "wide-retagger",
            project,
            "maintainer",
            {"REQ": {"read": True, "write": True, "visibility": ["internal", "customer"]}},
        ).headers
        moved = self.bloom.bloom_api_call(
            "PATCH", f"/api/requirements/{row}", wide, json={"req_origin": "Customer"}
        )
        self.assertEqual(
            (refused.status, refused.body["detail"], moved.status, moved.body["visibility"]),
            (values.STATUS_FORBIDDEN, values.TAG_HTTP_NO_EDIT, values.STATUS_OK, "customer"),
            msg=values.MSG_TAGH_VISIBILITY,
            abort_on_fail=False,
        )

    def bud_a_tag_only_a_read_policy_ticks_cannot_be_added(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TAG_HTTP_PREFIXES[8])["id"]
        seen = self.bloom.bloom_api_new_tag(self.admin, "read-only-tag")["id"]
        row = self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            self.admin,
            json={"project_id": project, "title": "Read tag", "req_origin": "Internal"},
        ).body["id"]
        user = self.bloom.bloom_api_ruled_member(
            self.admin,
            "read-tagger",
            project,
            "maintainer",
            {"REQ": {"read": True, "write": True, "visibility": ["internal"]}},
            {"REQ": {"read": True, "tags": [seen]}},
        ).headers
        refused = self.bloom.bloom_api_tag(user, "requirement", row, [seen])
        self.assertEqual(
            (refused.status, refused.body["detail"]),
            (values.STATUS_FORBIDDEN, values.TAG_HTTP_OUTSIDE),
            msg=values.MSG_TAGH_READ_TAG,
            abort_on_fail=False,
        )

    def bud_an_import_keeps_a_test_case_the_importer_cannot_edit(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TAG_HTTP_PREFIXES[9])["id"]
        internal = self.bloom.bloom_api_add_test_case(
            self.admin, project, "Kept", visibility="internal"
        ).body
        user = self.bloom.bloom_api_ruled_member(
            self.admin,
            "limited-importer",
            project,
            "maintainer",
            {"TC": {"read": True, "write": True, "visibility": ["customer"]}},
            {"TC": {"read": True, "visibility": ["internal"]}},
        ).headers
        csv = f"tc_id,title,visibility\n{internal['tc_id']},Overwritten,customer\n".encode()
        result = self.bloom.bloom_api_import_file(
            user, project, "test-cases", "cases.csv", csv, "text/csv", format="csv"
        )
        stored = self.bloom.bloom_api_call(
            "GET", f"/api/test-cases/{internal['id']}", self.admin
        ).body
        self.assertEqual(
            (result.status, result.body["updated"], stored["title"], stored["visibility"]),
            (values.STATUS_CREATED, 0, "Kept", "internal"),
            msg=values.MSG_TAGH_IMPORT_KEEPS,
            abort_on_fail=False,
        )

    def bud_an_external_account_neither_deletes_nor_approves(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.TAG_HTTP_PREFIXES[10])["id"]
        user = self.bloom.bloom_api_ruled_member(
            self.admin,
            "external-writer",
            project,
            "external",
            {
                "REQ": {
                    "read": True,
                    "write": True,
                    "approve": True,
                    "delete": True,
                    "visibility": ["customer"],
                }
            },
        ).headers
        rights = set(
            self.bloom.bloom_api_call("GET", f"/api/projects/{project}/permissions", user).body[
                "REQ"
            ]
        )
        own = self.bloom.bloom_api_call(
            "POST",
            "/api/requirements",
            user,
            json={"project_id": project, "title": "Own requirement"},
        )
        deleted = self.bloom.bloom_api_call("DELETE", f"/api/requirements/{own.body['id']}", user)
        self.assertEqual(
            (rights & {"approve", "delete"}, own.status, deleted.status),
            (set(), values.STATUS_CREATED, values.STATUS_FORBIDDEN),
            msg=values.MSG_TAGH_EXTERNAL_CAP,
            abort_on_fail=False,
        )
