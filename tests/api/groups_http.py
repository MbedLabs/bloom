"""
* @file     ${tests/api/groups_http.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the groups and policies routes and the access a group grant gives.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the groups and policies.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class GroupsHttpBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_the_default_policies_are_listed(self):
        values = self.parameters
        listed = self.bloom.bloom_api_call("GET", "/api/policies", self.admin)
        defaults = [policy for policy in listed.body if policy["is_default"]]
        self.assertEqual(
            (
                listed.status,
                any("base_role" in policy for policy in listed.body),
                len(defaults),
                {policy["name"] for policy in defaults},
            ),
            (values.STATUS_OK, False, 24, self.bloom.bloom_default_policy_names()),
            msg=values.MSG_GRP_LISTED,
            abort_on_fail=False,
        )
        origins = {"Read Customer": "customer", "Review Customer": "customer"}
        mismatched = [
            (policy["name"], doc_type)
            for policy in defaults
            for doc_type, rule in policy["rules"].items()
            if doc_type in self.bloom.bloom_document_types()
            and (
                rule["all_origins"] is not (policy["name"] not in origins),
                rule["visibility"]
                != ([origins[policy["name"]]] if policy["name"] in origins else []),
                rule["tags"] != [],
            )
            != (False, False, False)
        ]
        self.assertEqual(mismatched, [], msg=values.MSG_GRP_LISTED, abort_on_fail=False)

    def bud_a_review_only_policy_keeps_its_origin(self):
        values = self.parameters
        rule = values.GRP_REVIEW_RULE
        created = self.bloom.bloom_api_call(
            "POST",
            "/api/policies",
            self.admin,
            json={"name": "Review only", "scope": "document", "rules": {"REQ": rule}},
        )
        shown = self.bloom.bloom_api_call("GET", f"/api/policies/{created.body['id']}", self.admin)
        expected = {**rule, "all_origins": False, "tags": [], "actions": ["review"]}
        self.assertEqual(
            (created.status, shown.status, shown.body["rules"]["REQ"]),
            (values.STATUS_CREATED, values.STATUS_OK, expected),
            msg=values.MSG_GRP_REVIEW_CREATED,
            abort_on_fail=False,
        )
        internal = {**rule, "visibility": ["internal"]}
        updated = self.bloom.bloom_api_call(
            "PATCH",
            f"/api/policies/{created.body['id']}",
            self.admin,
            json={"rules": {"REQ": internal}},
        )
        self.assertEqual(
            (updated.status, updated.body["rules"]["REQ"]),
            (
                values.STATUS_OK,
                {**internal, "all_origins": False, "tags": [], "actions": ["review"]},
            ),
            msg=values.MSG_GRP_REVIEW_UPDATED,
            abort_on_fail=False,
        )
        unscoped = self.bloom.bloom_api_call(
            "POST",
            "/api/policies",
            self.admin,
            json={"name": "Unscoped review", "rules": {"REQ": {"review": True}}},
        )
        self.assertEqual(
            (unscoped.status, "Choose at least one tag for REQ" in unscoped.body["detail"]),
            (values.STATUS_BAD_REQUEST, True),
            msg=values.MSG_GRP_REVIEW_UNSCOPED,
            abort_on_fail=False,
        )

    def bud_the_review_defaults_review_only(self):
        values = self.parameters
        defaults = {
            policy["name"]: policy
            for policy in self.bloom.bloom_api_call("GET", "/api/policies", self.admin).body
            if policy["is_default"]
        }
        for name, origin in (("Review Internal", None), ("Review Customer", "customer")):
            rules = defaults[name]["rules"]
            wrong = [
                doc_type
                for doc_type, rule in rules.items()
                if (
                    rule["review"],
                    rule["read"],
                    rule["write"],
                    rule["approve"],
                    rule["delete"],
                    rule["all_origins"],
                    rule["visibility"],
                    rule["actions"],
                )
                != (
                    True,
                    False,
                    False,
                    False,
                    False,
                    origin is None,
                    [origin] if origin else [],
                    ["review"],
                )
            ]
            self.assertEqual(
                (set(rules), wrong),
                (self.bloom.bloom_document_types(), []),
                msg=values.MSG_GRP_REVIEW_DEFAULTS.format(
                    name=name, origin=" for customer content" if origin else " of every origin"
                ),
                abort_on_fail=False,
            )

    def bud_a_group_keeps_its_members_and_grants(self):
        values = self.parameters
        policy = self.bloom.bloom_api_rules_policy(self.admin, "Group CRUD policy", external=True)
        user = self.bloom.bloom_api_new_member(self.admin, "group-crud", "external")
        project = self.bloom.bloom_api_new_project(self.admin, values.GRP_PREFIXES[0])["id"]
        group = self.bloom.bloom_api_new_group(self.admin, "Group CRUD team", [policy["id"]])
        self.assertEqual(
            (group["members"], group["grants"], "policy_id" in group),
            ([], [], False),
            msg=values.MSG_GRP_NEW,
            abort_on_fail=False,
        )
        members = f"/api/groups/{group['id']}/members"
        added = self.bloom.bloom_api_call("POST", members, self.admin, json={"user_id": user.id})
        again = self.bloom.bloom_api_call("POST", members, self.admin, json={"user_id": user.id})
        self.assertEqual(
            (
                added.status,
                [(m["user_id"], m["email"]) for m in added.body["members"]],
                again.status,
            ),
            (values.STATUS_CREATED, [(user.id, user.email)], values.STATUS_CONFLICT),
            msg=values.MSG_GRP_MEMBER,
            abort_on_fail=False,
        )
        grants = f"/api/groups/{group['id']}/grants"
        granted = self.bloom.bloom_api_call(
            "POST", grants, self.admin, json={"project_id": project}
        )
        twice = self.bloom.bloom_api_call("POST", grants, self.admin, json={"project_id": project})
        self.assertEqual(
            (granted.status, [g["project_id"] for g in granted.body["grants"]], twice.status),
            (values.STATUS_CREATED, [project], values.STATUS_CONFLICT),
            msg=values.MSG_GRP_GRANT,
            abort_on_fail=False,
        )
        fetched = self.bloom.bloom_api_call("GET", f"/api/groups/{group['id']}", self.admin).body
        listed = {g["id"] for g in self.bloom.bloom_api_call("GET", "/api/groups", self.admin).body}
        self.assertEqual(
            (len(fetched["members"]), len(fetched["grants"]), group["id"] in listed),
            (1, 1, True),
            msg=values.MSG_GRP_READ,
            abort_on_fail=False,
        )
        removed = (
            self.bloom.bloom_api_call(
                "DELETE", f"{grants}/{granted.body['grants'][0]['id']}", self.admin
            ).status,
            self.bloom.bloom_api_call("DELETE", f"{members}/{user.id}", self.admin).status,
        )
        emptied = self.bloom.bloom_api_call("GET", f"/api/groups/{group['id']}", self.admin).body
        deleted = self.bloom.bloom_api_call(
            "DELETE", f"/api/groups/{group['id']}", self.admin
        ).status
        self.assertEqual(
            (
                removed,
                emptied["members"],
                emptied["grants"],
                deleted,
                self.bloom.bloom_api_call("GET", f"/api/groups/{group['id']}", self.admin).status,
            ),
            (
                (values.STATUS_NO_CONTENT,) * 2,
                [],
                [],
                values.STATUS_NO_CONTENT,
                values.STATUS_NOT_FOUND,
            ),
            msg=values.MSG_GRP_EMPTIED,
            abort_on_fail=False,
        )

    def bud_a_group_grant_gives_project_access(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "group-access")
        granted, other = (
            self.bloom.bloom_api_new_project(self.admin, values.GRP_PREFIXES[1])["id"],
            self.bloom.bloom_api_new_project(self.admin, values.GRP_PREFIXES[2])["id"],
        )
        reach = lambda project: self.bloom.bloom_api_call(
            "GET", f"/api/projects/{project}", user.headers
        ).status
        before = reach(granted)
        policy = self.bloom.bloom_api_rules_policy(self.admin, "Group access policy")
        group = self.bloom.bloom_api_new_group(self.admin, "Group access team", [policy["id"]])
        self.bloom.bloom_api_admit_group(self.admin, group["id"], granted)
        self.bloom.bloom_api_add_group_member(self.admin, group["id"], user.id)
        during = (reach(granted), reach(other))
        self.bloom.bloom_api_call(
            "DELETE", f"/api/groups/{group['id']}/members/{user.id}", self.admin
        )
        self.assertEqual(
            (before, during, reach(granted)),
            (
                values.STATUS_FORBIDDEN,
                (values.STATUS_OK, values.STATUS_FORBIDDEN),
                values.STATUS_FORBIDDEN,
            ),
            msg=values.MSG_GRP_ACCESS,
            abort_on_fail=False,
        )

    def bud_a_group_grant_admits_an_external_account(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "group-external", "external")
        project = self.bloom.bloom_api_new_project(self.admin, values.GRP_PREFIXES[3])["id"]
        before = self.bloom.bloom_api_call("GET", f"/api/projects/{project}", user.headers).status
        policy = self.bloom.bloom_api_rules_policy(
            self.admin, "External grant policy", ("REQ", "TC"), external=True
        )
        group = self.bloom.bloom_api_new_group(self.admin, "External grant team", [policy["id"]])
        self.bloom.bloom_api_admit_group(self.admin, group["id"], project)
        self.bloom.bloom_api_add_group_member(self.admin, group["id"], user.id)
        self.assertEqual(
            (
                before,
                self.bloom.bloom_api_call("GET", f"/api/projects/{project}", user.headers).status,
            ),
            (values.STATUS_FORBIDDEN, values.STATUS_OK),
            msg=values.MSG_GRP_EXTERNAL,
            abort_on_fail=False,
        )

    def bud_an_unknown_document_type_is_refused_400(self):
        values = self.parameters
        body = {"name": "Bad policy", "rules": {"NOPE": {"read": True, "visibility": ["customer"]}}}
        answer = self.bloom.bloom_api_call("POST", "/api/policies", self.admin, json=body)
        self.assertEqual(
            (answer.status, "NOPE" in str(answer.body)),
            (values.STATUS_BAD_REQUEST, True),
            msg=values.MSG_GRP_UNKNOWN_TYPE,
            abort_on_fail=False,
        )

    def bud_default_policies_are_protected(self):
        values = self.parameters
        default = next(
            policy
            for policy in self.bloom.bloom_api_call("GET", "/api/policies", self.admin).body
            if policy["is_default"]
        )
        path = f"/api/policies/{default['id']}"
        self.assertEqual(
            self.bloom.bloom_api_call("DELETE", path, self.admin).status,
            values.STATUS_BAD_REQUEST,
            msg=values.MSG_GRP_DEFAULT_DELETE,
            abort_on_fail=False,
        )
        for field, body in (
            ("name", {"name": "x"}),
            ("description", {"description": "x"}),
            ("rules", {"rules": {}}),
        ):
            changed = self.bloom.bloom_api_call("PATCH", path, self.admin, json=body)
            self.assertEqual(
                (changed.status, changed.body["detail"]),
                (values.STATUS_FORBIDDEN, values.GRP_READ_ONLY),
                msg=values.MSG_GRP_DEFAULT_CHANGE.format(field=field),
                abort_on_fail=False,
            )
        copy = self.bloom.bloom_api_call("POST", path + "/duplicate", self.admin)
        again = self.bloom.bloom_api_call("POST", path + "/duplicate", self.admin)
        edited = self.bloom.bloom_api_call(
            "PATCH", f"/api/policies/{copy.body['id']}", self.admin, json={"description": "mine"}
        )
        deleted = [
            self.bloom.bloom_api_call(
                "DELETE", f"/api/policies/{made.body['id']}", self.admin
            ).status
            for made in (copy, again)
        ]
        self.assertEqual(
            (
                copy.status,
                copy.body["name"],
                copy.body["is_default"],
                copy.body["rules"] == default["rules"],
                again.body["name"],
                edited.status,
                deleted,
            ),
            (
                values.STATUS_CREATED,
                f"{default['name']} (copy)",
                False,
                True,
                f"{default['name']} (copy 2)",
                values.STATUS_OK,
                [values.STATUS_NO_CONTENT] * 2,
            ),
            msg=values.MSG_GRP_COPIES,
            abort_on_fail=False,
        )
        custom = self.bloom.bloom_api_rules_policy(self.admin, "Custom policy", external=True)
        retuned = self.bloom.bloom_api_call(
            "PATCH",
            f"/api/policies/{custom['id']}",
            self.admin,
            json={"rules": {"REQ": {"read": True, "visibility": ["internal"]}}},
        )
        self.assertEqual(
            (
                custom["is_default"],
                retuned.status,
                retuned.body["rules"]["REQ"]["visibility"],
                self.bloom.bloom_api_call(
                    "DELETE", f"/api/policies/{custom['id']}", self.admin
                ).status,
            ),
            (False, values.STATUS_OK, ["internal"], values.STATUS_NO_CONTENT),
            msg=values.MSG_GRP_CUSTOM,
            abort_on_fail=False,
        )

    def bud_a_policy_in_use_cannot_be_deleted_409(self):
        values = self.parameters
        policy = self.bloom.bloom_api_rules_policy(self.admin, "Policy in use", external=True)
        group = self.bloom.bloom_api_new_group(self.admin, "Policy in use team", [policy["id"]])
        self.bloom.bloom_api_admit_group(
            self.admin,
            group["id"],
            self.bloom.bloom_api_new_project(self.admin, values.GRP_PREFIXES[4])["id"],
        )
        path = f"/api/policies/{policy['id']}"
        self.assertEqual(
            (
                self.bloom.bloom_api_call("DELETE", path, self.admin).status,
                self.bloom.bloom_api_call(
                    "DELETE", f"/api/groups/{group['id']}", self.admin
                ).status,
                self.bloom.bloom_api_call("DELETE", path, self.admin).status,
            ),
            (values.STATUS_CONFLICT, values.STATUS_NO_CONTENT, values.STATUS_NO_CONTENT),
            msg=values.MSG_GRP_IN_USE,
            abort_on_fail=False,
        )

    def bud_groups_and_policies_are_for_administrators_403(self):
        values = self.parameters
        user = self.bloom.bloom_api_new_member(self.admin, "not-an-admin", "external")
        answers = (
            self.bloom.bloom_api_call("GET", "/api/groups", user.headers).status,
            self.bloom.bloom_api_call("GET", "/api/policies", user.headers).status,
            self.bloom.bloom_api_call(
                "POST", "/api/groups", user.headers, json={"name": "Nope"}
            ).status,
        )
        self.assertEqual(
            answers,
            (values.STATUS_FORBIDDEN,) * 3,
            msg=values.MSG_GRP_ADMIN_ONLY,
            abort_on_fail=False,
        )
