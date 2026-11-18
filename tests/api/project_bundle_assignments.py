"""
* @file     ${tests/api/project_bundle_assignments.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests project bundle assignments and application grants.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the project bundle assignments.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ProjectBundleAssignmentsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_one_user_holds_different_bundles_on_two_projects(self):
        values = self.parameters
        projects = [
            self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[0])["id"],
            self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[1])["id"],
        ]
        user = self.bloom.bloom_api_new_member(self.admin, "two-bundles", "maintainer")
        write = self.bloom.bloom_api_new_policy(
            self.admin, "Two bundles write", {"REQ": ["view", "create", "edit"]}
        )
        read = self.bloom.bloom_api_new_policy(
            self.admin, "Two bundles read", visibility="customer"
        )
        bundles = [
            self.bloom.bloom_api_new_group(self.admin, "Writing bundle", [write["id"]]),
            self.bloom.bloom_api_new_group(self.admin, "Reading bundle", [read["id"]]),
        ]
        for project, bundle in zip(projects, bundles):
            self.bloom.bloom_api_admit(self.admin, project, user.id, policy_group_id=bundle["id"])
        first, second = (
            self.bloom.bloom_api_call(
                "GET", f"/api/projects/{projects[0]}/permissions", user.headers
            ).body,
            self.bloom.bloom_api_call(
                "GET", f"/api/projects/{projects[1]}/permissions", user.headers
            ).body,
        )
        members = [
            self.bloom.bloom_api_call("GET", f"/api/groups/{bundle['id']}", self.admin).body[
                "members"
            ]
            for bundle in bundles
        ]
        self.assertEqual(
            ("create" in first["REQ"], "create" in second["REQ"], members),
            (True, False, [[], []]),
            msg=values.MSG_PBA_TWO_BUNDLES,
            abort_on_fail=False,
        )
        created = [
            self.bloom.bloom_api_call(
                "POST",
                "/api/requirements",
                user.headers,
                json={
                    "project_id": project,
                    "title": f"Requirement {origin}",
                    "visibility": origin,
                },
            ).status
            for project, origin in zip(projects, ("internal", "customer"))
        ]
        self.assertEqual(
            created,
            [values.STATUS_CREATED, values.STATUS_FORBIDDEN],
            msg=values.MSG_PBA_CREATE,
            abort_on_fail=False,
        )
        changed = self.bloom.bloom_api_call(
            "PATCH",
            f"/api/groups/{bundles[0]['id']}",
            self.admin,
            json={"policy_ids": [read["id"]]},
        )
        self.assertEqual(
            (
                changed.status,
                "create"
                in self.bloom.bloom_api_call(
                    "GET", f"/api/projects/{projects[0]}/permissions", user.headers
                ).body["REQ"],
            ),
            (values.STATUS_OK, False),
            msg=values.MSG_PBA_BUNDLE_CHANGED,
            abort_on_fail=False,
        )

    def bud_an_access_manager_assigns_atomically(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[2])["id"]
        manager = self.bloom.bloom_api_new_member(self.admin, "access-manager", "maintainer")
        people = [
            self.bloom.bloom_api_new_member(self.admin, "assigned-one", "maintainer"),
            self.bloom.bloom_api_new_member(self.admin, "assigned-two", "maintainer"),
        ]
        self.assertEqual(
            self.bloom.bloom_api_call("GET", "/api/tags", manager.headers).status,
            values.STATUS_FORBIDDEN,
            msg=values.MSG_PBA_MANAGER_BEFORE,
            abort_on_fail=False,
        )
        access = self.bloom.bloom_api_default_named(self.admin, "policies", "Access Management")
        read = self.bloom.bloom_api_default_named(self.admin, "policies", "Read Customer")
        granted = self.bloom.bloom_api_set_application_policies(
            self.admin, manager.id, [access["id"]]
        )
        reach = [
            self.bloom.bloom_api_call("GET", path, manager.headers).status
            for path in (
                "/api/tags",
                "/api/users",
                f"/api/projects/{project}",
                "/api/groups/assignment-options",
            )
        ]
        self.assertEqual(
            (granted.status, reach),
            (
                values.STATUS_OK,
                [
                    values.STATUS_OK,
                    values.STATUS_FORBIDDEN,
                    values.STATUS_FORBIDDEN,
                    values.STATUS_OK,
                ],
            ),
            msg=values.MSG_PBA_MANAGER_REACH,
            abort_on_fail=False,
        )
        bundle = self.bloom.bloom_api_new_group(self.admin, "Manager bundle", [read["id"]])
        before = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/members", self.admin
        ).body
        invalid = self.bloom.bloom_api_assign_bundle(
            manager.headers, bundle["id"], project, [people[0].id, values.PBA_MISSING]
        )
        self.assertEqual(
            (
                invalid.status,
                self.bloom.bloom_api_call(
                    "GET", f"/api/projects/{project}/members", self.admin
                ).body,
            ),
            (values.STATUS_NOT_FOUND, before),
            msg=values.MSG_PBA_ATOMIC,
            abort_on_fail=False,
        )
        assigned = self.bloom.bloom_api_assign_bundle(
            manager.headers, bundle["id"], project, [person.id for person in people]
        )
        self.assertEqual(
            (
                assigned.status,
                {entry["policy_group_id"] for entry in assigned.body},
                len(
                    self.bloom.bloom_api_call(
                        "GET", f"/api/projects/{project}/members", self.admin
                    ).body
                ),
                self.bloom.bloom_api_call(
                    "GET", f"/api/projects/{project}", manager.headers
                ).status,
                self.bloom.bloom_api_call("GET", "/api/users", manager.headers).status,
                bool(
                    self.bloom.bloom_api_call("GET", "/api/auth/me", manager.headers).body[
                        "application_permissions"
                    ]["access"]
                ),
            ),
            (
                values.STATUS_OK,
                {bundle["id"]},
                len(before) + 2,
                values.STATUS_FORBIDDEN,
                values.STATUS_FORBIDDEN,
                True,
            ),
            msg=values.MSG_PBA_ASSIGNED,
            abort_on_fail=False,
        )

    def bud_the_administrators_bundle_gives_no_app_administration(self):
        values = self.parameters
        first, second = (
            self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[3])["id"],
            self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[4])["id"],
        )
        user = self.bloom.bloom_api_new_member(self.admin, "project-administrator", "maintainer")
        bundle = self.bloom.bloom_api_default_named(self.admin, "groups", "Administrators")
        self.bloom.bloom_api_admit(self.admin, first, user.id, policy_group_id=bundle["id"])
        answers = (
            self.bloom.bloom_api_call(
                "PATCH", f"/api/projects/{first}", user.headers, json={"description": "Updated"}
            ).status,
            self.bloom.bloom_api_call("GET", f"/api/projects/{second}", user.headers).status,
            self.bloom.bloom_api_call("GET", "/api/groups", user.headers).status,
            self.bloom.bloom_api_call("GET", "/api/users", user.headers).status,
            self.bloom.bloom_api_call("DELETE", f"/api/projects/{first}", user.headers).status,
        )
        self.assertEqual(
            answers,
            (values.STATUS_OK,) + (values.STATUS_FORBIDDEN,) * 4,
            msg=values.MSG_PBA_ADMINISTRATORS,
            abort_on_fail=False,
        )

    def bud_a_content_policy_cannot_be_an_application_policy_400(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "content-app", "external")
        policy = self.bloom.bloom_api_new_policy(self.admin, "Content app policy")
        rejected = self.bloom.bloom_api_set_application_policies(
            self.admin, user.id, [policy["id"]]
        )
        self.assertEqual(
            (
                rejected.status,
                self.bloom.bloom_api_call("GET", f"/api/users/{user.id}", self.admin).body["role"],
            ),
            (values.STATUS_BAD_REQUEST, "external"),
            msg=values.MSG_PBA_CONTENT_APP,
            abort_on_fail=False,
        )

    def bud_an_external_access_manager_keeps_the_external_limits(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "external-manager", "external")
        access = self.bloom.bloom_api_default_named(self.admin, "policies", "Access Management")
        saved = self.bloom.bloom_api_set_application_policies(self.admin, user.id, [access["id"]])
        allowed = self.bloom.bloom_api_call(
            "GET", "/api/users/me/application-permissions", user.headers
        ).body["access"]
        self.assertEqual(
            (
                saved.status,
                "edit" in allowed,
                "delete" in allowed,
                self.bloom.bloom_api_call(
                    "GET", "/api/groups/assignment-options", user.headers
                ).status,
                self.bloom.bloom_api_call("GET", "/api/projects", user.headers).body,
                self.bloom.bloom_api_call("GET", f"/api/users/{user.id}", self.admin).body["role"],
            ),
            (values.STATUS_OK, True, False, values.STATUS_OK, [], "external"),
            msg=values.MSG_PBA_VIEWER,
            abort_on_fail=False,
        )

    def bud_a_bundle_entry_refuses_mixed_modes(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[5])["id"]
        user = self.bloom.bloom_api_new_member(self.admin, "mixed-modes", "maintainer")
        group = self.bloom.bloom_api_new_group(
            self.admin,
            "Mixed modes bundle",
            [self.bloom.bloom_api_new_policy(self.admin, "Mixed modes policy")["id"]],
        )
        mixed = self.bloom.bloom_api_admit(
            self.admin, project, user.id, policy_group_id=group["id"], owner=True
        )
        missing = self.bloom.bloom_api_admit(
            self.admin, project, user.id, policy_group_id=values.PBA_MISSING
        )
        valid = self.bloom.bloom_api_admit(
            self.admin, project, user.id, policy_group_id=group["id"]
        )
        entry = f"/api/projects/{project}/members/{valid.body['id']}"
        rejected = self.bloom.bloom_api_call(
            "PATCH",
            entry,
            self.admin,
            json={"policy_group_id": group["id"], "inherit_policies": True},
        )
        self.assertEqual(
            (
                mixed.status,
                missing.status,
                valid.status,
                rejected.status,
                self.bloom.bloom_api_call("GET", entry, self.admin).body["policy_group_id"],
            ),
            (
                values.STATUS_UNPROCESSABLE,
                values.STATUS_NOT_FOUND,
                values.STATUS_CREATED,
                values.STATUS_UNPROCESSABLE,
                group["id"],
            ),
            msg=values.MSG_PBA_MIXED,
            abort_on_fail=False,
        )

    def bud_an_assigned_application_policy_keeps_its_scope_409(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "app-scope", "maintainer")
        body = {
            "name": "App scope guard",
            "scope": "app",
            "rules": {"access": {"read": True, "write": True, "delete": True}},
        }
        policy = self.bloom.bloom_api_call("POST", "/api/policies", self.admin, json=body).body
        first = self.bloom.bloom_api_set_application_policies(
            self.admin, user.id, [policy["id"]]
        ).status
        changed = self.bloom.bloom_api_call(
            "PATCH",
            f"/api/policies/{policy['id']}",
            self.admin,
            json={"scope": "project", "rules": {"project": {"read": True}}},
        )
        self.assertEqual(
            (
                first,
                changed.status,
                self.bloom.bloom_api_call("GET", f"/api/policies/{policy['id']}", self.admin).body[
                    "scope"
                ],
                self.bloom.bloom_api_set_application_policies(
                    self.admin, user.id, [policy["id"]]
                ).status,
            ),
            (values.STATUS_OK, values.STATUS_CONFLICT, "app", values.STATUS_OK),
            msg=values.MSG_PBA_APP_SCOPE,
            abort_on_fail=False,
        )

    def bud_the_administrators_bundle_serves_two_rosters(self):
        values = self.parameters
        projects = [
            self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[6])["id"],
            self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[7])["id"],
        ]
        people = [
            self.bloom.bloom_api_new_member(self.admin, "roster-one", "maintainer"),
            self.bloom.bloom_api_new_member(self.admin, "roster-two", "maintainer"),
        ]
        account_admin = self.bloom.bloom_api_new_member(self.admin, "roster-admin", "admin")
        bundle = self.bloom.bloom_api_default_named(self.admin, "groups", "Administrators")
        choices = {
            person["id"]
            for person in self.bloom.bloom_api_call(
                "GET", "/api/groups/assignment-options", self.admin
            ).body["users"]
        }
        self.assertTrue(
            account_admin.id in choices,
            msg=values.MSG_PBA_ROSTER.format(who="an account administrator"),
            abort_on_fail=False,
        )
        for project, person in zip(projects, people):
            answer = self.bloom.bloom_api_assign_bundle(
                self.admin, bundle["id"], project, [person.id, account_admin.id]
            )
            other = next(value for value in projects if value != project)
            self.assertEqual(
                (
                    answer.status,
                    {entry["user_id"] for entry in answer.body},
                    self.bloom.bloom_api_call(
                        "PATCH",
                        f"/api/projects/{project}",
                        person.headers,
                        json={"description": "Updated"},
                    ).status,
                    self.bloom.bloom_api_call(
                        "GET", f"/api/projects/{other}", person.headers
                    ).status,
                    self.bloom.bloom_api_call("GET", "/api/users", person.headers).status,
                ),
                (
                    values.STATUS_OK,
                    {person.id, account_admin.id},
                    values.STATUS_OK,
                    values.STATUS_FORBIDDEN,
                    values.STATUS_FORBIDDEN,
                ),
                msg=values.MSG_PBA_ROSTER.format(who="a different person"),
                abort_on_fail=False,
            )
        self.assertEqual(
            (
                self.bloom.bloom_api_call("GET", f"/api/groups/{bundle['id']}", self.admin).body[
                    "members"
                ],
                self.bloom.bloom_api_call("GET", f"/api/users/{account_admin.id}", self.admin).body[
                    "role"
                ],
            ),
            ([], "admin"),
            msg=values.MSG_PBA_ROSTER_KEPT,
            abort_on_fail=False,
        )

    def bud_overlapping_bundles_keep_both_rights(self):
        values = self.parameters
        project, other = (
            self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[8])["id"],
            self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[9])["id"],
        )
        person = self.bloom.bloom_api_new_member(self.admin, "overlapping", "maintainer")
        author = self.bloom.bloom_api_new_group(
            self.admin,
            "Overlap author",
            [
                self.bloom.bloom_api_new_policy(
                    self.admin, "Overlap author policy", {"REQ": ["edit"]}
                )["id"]
            ],
        )
        tester = self.bloom.bloom_api_new_group(
            self.admin,
            "Overlap tester",
            [
                self.bloom.bloom_api_new_policy(
                    self.admin, "Overlap tester policy", {"TC": ["edit"]}
                )["id"]
            ],
        )
        first = self.bloom.bloom_api_assign_bundle(
            self.admin, author["id"], project, [person.id]
        ).body[0]
        second = self.bloom.bloom_api_assign_bundle(
            self.admin, tester["id"], project, [person.id]
        ).body[0]
        again = self.bloom.bloom_api_assign_bundle(
            self.admin, author["id"], project, [person.id]
        ).body[0]
        entries = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/members", self.admin
        ).body
        held = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/permissions", person.headers
        ).body
        shown = next(
            row
            for row in self.bloom.bloom_api_call(
                "GET", f"/api/projects/{project}/access", self.admin
            ).body
            if row["user_id"] == person.id
        )
        self.assertEqual(
            (
                first["id"] != second["id"],
                again["id"] == first["id"],
                {row["policy_group_id"] for row in entries if row["user_id"] == person.id},
                "edit" in held["REQ"] and "edit" in held["TC"],
                {origin["group"] for origin in shown["origins"]},
                self.bloom.bloom_api_call("GET", f"/api/projects/{other}", person.headers).status,
                self.bloom.bloom_api_call("GET", "/api/groups", person.headers).status,
            ),
            (
                True,
                True,
                {author["id"], tester["id"]},
                True,
                {author["name"], tester["name"]},
                values.STATUS_FORBIDDEN,
                values.STATUS_FORBIDDEN,
            ),
            msg=values.MSG_PBA_OVERLAP,
            abort_on_fail=False,
        )
        removed = self.bloom.bloom_api_call(
            "DELETE", f"/api/projects/{project}/members/{first['id']}", self.admin
        ).status
        held = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}/permissions", person.headers
        ).body
        self.assertEqual(
            (
                removed,
                "REQ" in held,
                "edit" in held.get("TC", []),
                self.bloom.bloom_api_call("GET", f"/api/users/{person.id}", self.admin).body[
                    "role"
                ],
                self.bloom.bloom_api_call("GET", f"/api/groups/{tester['id']}", self.admin).body[
                    "members"
                ],
            ),
            (values.STATUS_NO_CONTENT, False, True, "maintainer", []),
            msg=values.MSG_PBA_OVERLAP_REMOVED,
            abort_on_fail=False,
        )

    def bud_bundle_entries_refuse_duplicates_409(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[10])["id"]
        person = self.bloom.bloom_api_new_member(self.admin, "duplicate-entries", "maintainer")
        groups = [
            self.bloom.bloom_api_new_group(
                self.admin,
                "Duplicate bundle one",
                [self.bloom.bloom_api_new_policy(self.admin, "Duplicate policy one")["id"]],
            ),
            self.bloom.bloom_api_new_group(
                self.admin,
                "Duplicate bundle two",
                [self.bloom.bloom_api_new_policy(self.admin, "Duplicate policy two")["id"]],
            ),
        ]
        first = self.bloom.bloom_api_assign_bundle(
            self.admin, groups[0]["id"], project, [person.id]
        ).body[0]
        created = self.bloom.bloom_api_admit(
            self.admin, project, person.id, policy_group_id=groups[1]["id"]
        )
        changes = [
            self.bloom.bloom_api_call(
                "PATCH", f"/api/projects/{project}/members/{first['id']}", self.admin, json=body
            ).status
            for body in (
                {"policy_group_id": groups[1]["id"]},
                {"owner": True},
                {"inherit_policies": True},
            )
        ]
        duplicate = self.bloom.bloom_api_admit(
            self.admin, project, person.id, policy_group_id=groups[1]["id"]
        )
        entries = [
            row
            for row in self.bloom.bloom_api_call(
                "GET", f"/api/projects/{project}/members", self.admin
            ).body
            if row["user_id"] == person.id
        ]
        self.assertEqual(
            (created.status, changes, duplicate.status, len(entries)),
            (values.STATUS_CREATED, [values.STATUS_CONFLICT] * 3, values.STATUS_CONFLICT, 2),
            msg=values.MSG_PBA_DUPLICATES,
            abort_on_fail=False,
        )

    def bud_a_failed_batch_and_another_project_stay_unchanged(self):
        values = self.parameters
        projects = [
            self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[11])["id"],
            self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[12])["id"],
        ]
        person = self.bloom.bloom_api_new_member(self.admin, "independent", "maintainer")
        groups = [
            self.bloom.bloom_api_new_group(
                self.admin,
                "Independent bundle one",
                [self.bloom.bloom_api_new_policy(self.admin, "Independent policy one")["id"]],
            ),
            self.bloom.bloom_api_new_group(
                self.admin,
                "Independent bundle two",
                [self.bloom.bloom_api_new_policy(self.admin, "Independent policy two")["id"]],
            ),
        ]
        first = self.bloom.bloom_api_assign_bundle(
            self.admin, groups[0]["id"], projects[0], [person.id]
        ).body[0]
        untouched = self.bloom.bloom_api_assign_bundle(
            self.admin, groups[0]["id"], projects[1], [person.id]
        ).body[0]
        invalid = self.bloom.bloom_api_assign_bundle(
            self.admin, groups[1]["id"], projects[0], [person.id, values.PBA_MISSING]
        )
        kept = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{projects[0]}/members/{first['id']}", self.admin
        ).body
        self.bloom.bloom_api_assign_bundle(self.admin, groups[1]["id"], projects[0], [person.id])
        other = self.bloom.bloom_api_call(
            "GET", f"/api/projects/{projects[1]}/members/{untouched['id']}", self.admin
        ).body
        self.assertEqual(
            (invalid.status, kept, other),
            (values.STATUS_NOT_FOUND, first, untouched),
            msg=values.MSG_PBA_INDEPENDENT,
            abort_on_fail=False,
        )

    def bud_simultaneous_assignments_keep_one_entry_per_bundle(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[13])["id"]
        person = self.bloom.bloom_api_new_member(self.admin, "concurrent", "maintainer")
        groups = [
            self.bloom.bloom_api_new_group(
                self.admin,
                "Concurrent bundle one",
                [self.bloom.bloom_api_new_policy(self.admin, "Concurrent policy one")["id"]],
            ),
            self.bloom.bloom_api_new_group(
                self.admin,
                "Concurrent bundle two",
                [self.bloom.bloom_api_new_policy(self.admin, "Concurrent policy two")["id"]],
            ),
        ]
        for what, selection in (
            ("two bundles", groups),
            ("one bundle twice", [groups[0], groups[0]]),
        ):
            entries = self.bloom.bloom_api_assign_bundles_at_once(
                self.admin, project, person.id, [bundle["id"] for bundle in selection]
            )
            rows = [
                row
                for row in self.bloom.bloom_api_call(
                    "GET", f"/api/projects/{project}/members", self.admin
                ).body
                if row["user_id"] == person.id
            ]
            self.assertEqual(
                (
                    all(entry["user_id"] == person.id for entry in entries),
                    sorted(row["policy_group_id"] for row in rows),
                ),
                (True, sorted(bundle["id"] for bundle in groups)),
                msg=values.MSG_PBA_CONCURRENT.format(what=what),
                abort_on_fail=False,
            )

    def bud_the_first_bundle_replaces_an_owner_entry(self):
        values = self.parameters
        project = self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[14])["id"]
        person = self.bloom.bloom_api_new_member(self.admin, "legacy-owner", "maintainer")
        legacy = self.bloom.bloom_api_admit(self.admin, project, person.id, owner=True)
        groups = [
            self.bloom.bloom_api_new_group(
                self.admin,
                "Legacy bundle one",
                [self.bloom.bloom_api_new_policy(self.admin, "Legacy policy one")["id"]],
            ),
            self.bloom.bloom_api_new_group(
                self.admin,
                "Legacy bundle two",
                [self.bloom.bloom_api_new_policy(self.admin, "Legacy policy two")["id"]],
            ),
        ]
        first = self.bloom.bloom_api_assign_bundle(
            self.admin, groups[0]["id"], project, [person.id]
        ).body[0]
        second = self.bloom.bloom_api_assign_bundle(
            self.admin, groups[1]["id"], project, [person.id]
        ).body[0]
        self.assertEqual(
            (
                legacy.status,
                (first["id"] == legacy.body["id"], first["owner"], first["policy_group_id"]),
                second["id"] != first["id"],
                self.bloom.bloom_api_call(
                    "GET", f"/api/projects/{project}/members/{first['id']}", self.admin
                ).body,
            ),
            (values.STATUS_CREATED, (True, False, groups[0]["id"]), True, first),
            msg=values.MSG_PBA_LEGACY,
            abort_on_fail=False,
        )

    def bud_the_audit_names_each_bundle_entry(self):
        values = self.parameters
        actor = self.bloom.bloom_api_call("GET", "/api/auth/me", self.admin).body["id"]
        project = self.bloom.bloom_api_new_project(self.admin, values.PBA_PREFIXES[15])["id"]
        person = self.bloom.bloom_api_new_member(self.admin, "audited", "maintainer")
        groups = [
            self.bloom.bloom_api_new_group(
                self.admin,
                f"Audited bundle {n}",
                [self.bloom.bloom_api_new_policy(self.admin, f"Audited policy {n}")["id"]],
            )
            for n in range(3)
        ]
        entries = [
            self.bloom.bloom_api_admit(
                self.admin, project, person.id, policy_group_id=group["id"]
            ).body
            for group in groups[:2]
        ]
        updated = self.bloom.bloom_api_call(
            "PATCH",
            f"/api/projects/{project}/members/{entries[0]['id']}",
            self.admin,
            json={"policy_group_id": groups[2]["id"]},
        )
        removed = self.bloom.bloom_api_call(
            "DELETE", f"/api/projects/{project}/members/{entries[1]['id']}", self.admin
        )
        query = {"action": "project_member.", "target_id": str(person.id), "project_id": project}
        events = self.bloom.bloom_api_call("GET", "/api/audit", self.admin, params=query).body[
            "items"
        ]
        self.print_variables({"events": [(event["action"], event["details"]) for event in events]})
        added = {
            (event["details"].get("membership_id"), event["details"].get("policy_group_id"))
            for event in events
            if event["action"] == "project_member.added"
        }
        changed = next(
            event["details"] for event in events if event["action"] == "project_member.updated"
        )
        deleted = next(
            event["details"] for event in events if event["action"] == "project_member.removed"
        )
        self.assertEqual(
            (
                updated.status,
                removed.status,
                len(events),
                all(
                    (
                        event["actor_user_id"],
                        event["target_type"],
                        event["target_id"],
                        event["project_id"],
                        event["outcome"],
                    )
                    == (actor, "user", str(person.id), project, "success")
                    for event in events
                ),
                added,
                (
                    changed["membership_id"],
                    changed["policy_group_id"],
                    changed["previous_policy_group_id"],
                ),
                (deleted["membership_id"], deleted["policy_group_id"]),
            ),
            (
                values.STATUS_OK,
                values.STATUS_NO_CONTENT,
                4,
                True,
                {(entry["id"], group["id"]) for entry, group in zip(entries, groups[:2])},
                (entries[0]["id"], groups[2]["id"], groups[0]["id"]),
                (entries[1]["id"], groups[1]["id"]),
            ),
            msg=values.MSG_PBA_AUDIT,
            abort_on_fail=False,
        )
