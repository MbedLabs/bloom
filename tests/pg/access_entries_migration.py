"""
* @file     ${tests/pg/access_entries_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the access-entries migration on PostgreSQL.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the access-entries migration.
"""

import json

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class AccessEntriesMigrationBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_a_downgrade_and_upgrade_restore_the_same_state(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        down, down_log = self.bloom.bloom_run_alembic("downgrade", values.AEM_BEFORE)
        leftover = {
            "policies",
            "groups",
            "project_access",
            "tags",
        } & self.bloom.bloom_public_tables()
        up, up_log = self.bloom.bloom_run_alembic("upgrade", "head")
        self.print_variables({"downgrade": down_log[-400:], "upgrade": up_log[-400:]})
        self.assertEqual(
            (down, leftover, up, self.bloom.bloom_access_state() == self.state),
            (0, set(), 0, True),
            msg=values.MSG_AEM_ROUND_TRIP,
            abort_on_fail=False,
        )

    def bud_the_default_policies_are_seeded(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        policies_spec, _ = self.bloom.bloom_default_specs()
        policies = self.state["policies"]
        defaults = {name for name, row in policies.items() if row["is_default"]}
        self.assertEqual(
            (defaults, len(defaults)),
            ({spec["name"] for spec in policies_spec}, 24),
            msg=values.MSG_AEM_DEFAULTS,
            abort_on_fail=False,
        )
        for spec in policies_spec:
            stored = policies[spec["name"]]
            self.assertEqual(
                (
                    stored["scope"],
                    stored["description"],
                    json.loads(stored["permissions"]),
                    json.loads(stored["type_tags"]),
                ),
                (spec["scope"], spec["description"], spec["permissions"], spec["type_tags"]),
                msg=values.MSG_AEM_DEFAULT_SPEC.format(name=spec["name"]),
                abort_on_fail=False,
            )

    def bud_the_default_groups_are_seeded_without_members(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        _, groups_spec = self.bloom.bloom_default_specs()
        self.assertEqual(
            (self.state["groups"], self.state["members"], self.state["creator"]),
            ({spec["name"]: sorted(spec["policy_names"]) for spec in groups_spec}, 0, 1),
            msg=values.MSG_AEM_GROUPS,
            abort_on_fail=False,
        )

    def bud_released_memberships_become_entries(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        policies_spec, _ = self.bloom.bloom_default_specs()
        entries = self.state["entries"]
        expected = sorted(
            spec["name"] for spec in policies_spec if spec["name"] not in values.AEM_NOT_MAINTAINER
        )
        self.assertEqual(
            entries[self.ids["maintainer"]],
            (False, expected),
            msg=values.MSG_AEM_MAINTAINER,
            abort_on_fail=False,
        )
        for who, policy in values.AEM_RELEASED.items():
            self.assertEqual(
                entries.get(self.ids[who]),
                (False, [policy]),
                msg=values.MSG_AEM_RELEASED.format(who=who, policy=policy),
                abort_on_fail=False,
            )
        self.assertEqual(
            (self.ids["admin"] in entries, set(entries)),
            (
                False,
                {self.ids[user] for user in ("maintainer", "viewer", "every", "chosen", "empty")},
            ),
            msg=values.MSG_AEM_ADMIN,
            abort_on_fail=False,
        )

    def bud_the_account_roles_are_kept(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        roles = self.state["roles"]
        self.assertEqual(
            [
                roles[self.ids[user]]
                for user in ("maintainer", "viewer", "every", "chosen", "empty", "admin")
            ],
            ["maintainer", "maintainer", "external", "external", "external", "admin"],
            msg=values.MSG_AEM_ROLES,
            abort_on_fail=False,
        )

    def bud_the_released_read_policies_grant_reading_only(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        policies = self.state["policies"]
        for policy in values.AEM_RELEASED.values():
            row = policies[policy]
            permissions = json.loads(row["permissions"])
            self.assertEqual(
                (
                    row["is_default"],
                    "parameter" in permissions,
                    all(set(actions) <= {"view", "comment"} for actions in permissions.values()),
                    any(scope.get("all") for scope in json.loads(row["type_tags"]).values()),
                ),
                (False, False, True, False),
                msg=values.MSG_AEM_READ_ONLY.format(policy=policy),
                abort_on_fail=False,
            )
        chosen = policies[values.AEM_RELEASED["chosen"]]
        customer = {"visibility": ["customer"], "tags": []}
        self.assertEqual(
            (json.loads(chosen["type_tags"]), "SPEC" in json.loads(chosen["permissions"])),
            ({"REQ": customer, "TC": customer}, False),
            msg=values.MSG_AEM_CHOSEN,
            abort_on_fail=False,
        )
        empty = json.loads(policies[values.AEM_RELEASED["empty"]]["permissions"])
        self.assertEqual(
            set(empty),
            {"baseline", "link", "project"},
            msg=values.MSG_AEM_NO_TYPES,
            abort_on_fail=False,
        )
        every = json.loads(policies[values.AEM_RELEASED["every"]]["type_tags"])
        self.assertEqual(
            (set(every), all(rule == customer for rule in every.values())),
            (self.bloom.bloom_document_resources() - {"VIS"}, True),
            msg=values.MSG_AEM_ALL_TYPES,
            abort_on_fail=False,
        )
        read_only = json.loads(policies[values.AEM_RELEASED["viewer"]]["type_tags"])
        self.assertTrue(
            all(
                rule == {"visibility": ["internal", "customer"], "tags": []}
                for rule in read_only.values()
            ),
            msg=values.MSG_AEM_READ_TAGS,
            abort_on_fail=False,
        )

    def bud_the_maintainer_entry_covers_every_document_and_project_right(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        full = {}
        for name in self.state["entries"][self.ids["maintainer"]][1]:
            for resource, actions in json.loads(
                self.state["policies"][name]["permissions"]
            ).items():
                full.setdefault(resource, set()).update(actions)
        expected = {
            resource: actions - ({"review"} if resource in values.AEM_NO_REVIEW else set())
            for resource, actions in self.bloom.bloom_resource_action_sets().items()
            if resource not in values.AEM_APPLICATION
        }
        self.assertEqual(full, expected, msg=values.MSG_AEM_FULL, abort_on_fail=False)

    def bud_the_access_suites_pass_on_the_migrated_database(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        values = self.parameters
        for suite in values.AEM_SUITES:
            code, tail = self.bloom.bloom_run_suite_on_migrated_database(suite)
            if code:
                self.print_variables({suite: tail})
            self.assertEqual(
                code,
                0,
                msg=values.MSG_AEM_SUITE.format(suite=suite.rsplit(".", 1)[1]),
                abort_on_fail=False,
            )
