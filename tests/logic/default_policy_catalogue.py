"""
* @file     ${tests/logic/default_policy_catalogue.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the default policy and group catalogue.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the default policy catalogue.
"""

import copy

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class DefaultPolicyCatalogueBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_the_catalogue_holds_the_24_named_policies(self):
        policies, groups = self.bloom.bloom_default_catalogue()
        by_name = {policy["name"]: policy for policy in policies}
        actions = self.bloom.bloom_resource_actions()
        values = self.parameters
        self.assertEqual(
            (len(policies), len(by_name), set(by_name), set(values.CAT_DOCUMENT_POLICIES.values())),
            (
                values.CAT_COUNT,
                values.CAT_COUNT,
                set(values.CAT_DOCUMENT_POLICIES) | values.CAT_OTHER_POLICIES,
                set(self.bloom.bloom_permission_resources_of_documents()),
            ),
            msg=values.MSG_CAT_NAMES,
            abort_on_fail=False,
        )

    def bud_each_document_policy_covers_its_own_type(self):
        policies, groups = self.bloom.bloom_default_catalogue()
        by_name = {policy["name"]: policy for policy in policies}
        actions = self.bloom.bloom_resource_actions()
        values = self.parameters
        for name, resource in values.CAT_DOCUMENT_POLICIES.items():
            policy = by_name[name]
            expected = actions[resource] - (
                {"review"} if resource in values.CAT_NO_REVIEW else set()
            )
            self.assertEqual(
                (
                    policy["scope"],
                    set(policy["permissions"]),
                    set(policy["permissions"][resource]),
                    policy["type_tags"][resource],
                ),
                ("document", {resource}, expected, {"all": True, "visibility": [], "tags": []}),
                msg=values.MSG_CAT_DOCUMENT.format(name=name, resource=resource),
                abort_on_fail=False,
            )

    def bud_each_project_policy_covers_its_own_resource(self):
        policies, groups = self.bloom.bloom_default_catalogue()
        by_name = {policy["name"]: policy for policy in policies}
        actions = self.bloom.bloom_resource_actions()
        for name, resource in self.parameters.CAT_PROJECT_POLICIES:
            policy = by_name[name]
            self.assertEqual(
                (policy["scope"], set(policy["permissions"]), set(policy["permissions"][resource])),
                ("project", {resource}, actions[resource]),
                msg=self.parameters.MSG_CAT_PROJECT.format(name=name, resource=resource),
                abort_on_fail=False,
            )

    def bud_the_reader_policies_give_view_and_comment_for_their_origin(self):
        policies, groups = self.bloom.bloom_default_catalogue()
        by_name = {policy["name"]: policy for policy in policies}
        actions = self.bloom.bloom_resource_actions()
        for name, origin in self.parameters.CAT_READERS:
            policy = by_name[name]
            self.assertEqual(
                (
                    policy["scope"],
                    set(policy["permissions"]),
                    all(
                        set(granted) <= {"view", "comment"}
                        for granted in policy["permissions"].values()
                    ),
                    all(
                        rule
                        == {
                            "all": origin is None,
                            "visibility": [origin] if origin else [],
                            "tags": [],
                        }
                        for rule in policy["type_tags"].values()
                    ),
                ),
                ("project", set(self.bloom.bloom_resources()), True, True),
                msg=self.parameters.MSG_CAT_READER.format(name=name),
                abort_on_fail=False,
            )

    def bud_the_app_policies_cover_access_and_administration(self):
        policies, groups = self.bloom.bloom_default_catalogue()
        by_name = {policy["name"]: policy for policy in policies}
        actions = self.bloom.bloom_resource_actions()
        access, admin = by_name["Access Management"], by_name["Application Administration"]
        self.assertEqual(
            (
                access["scope"],
                set(access["permissions"]),
                set(access["permissions"]["access"]),
                access["type_tags"],
            ),
            ("app", {"access"}, actions["access"], {}),
            msg=self.parameters.MSG_CAT_ACCESS,
            abort_on_fail=False,
        )
        self.assertEqual(
            (
                admin["scope"],
                {resource: set(granted) for resource, granted in admin["permissions"].items()},
            ),
            ("app", actions),
            msg=self.parameters.MSG_CAT_ADMIN,
            abort_on_fail=False,
        )

    def bud_the_default_groups_hold_policies_and_no_people(self):
        policies, groups = self.bloom.bloom_default_catalogue()
        by_name = {policy["name"]: policy for policy in policies}
        actions = self.bloom.bloom_resource_actions()
        values = self.parameters
        self.assertEqual(
            (
                {group["name"] for group in groups},
                all(group["policy_names"] for group in groups),
                all(
                    len(group["policy_names"]) == len(set(group["policy_names"]))
                    for group in groups
                ),
                all(set(group["policy_names"]) <= set(by_name) for group in groups),
                any({"user_ids", "project_ids"} & group.keys() for group in groups),
            ),
            (values.CAT_GROUPS, True, True, True, False),
            msg=values.MSG_CAT_GROUPS,
            abort_on_fail=False,
        )
        for group in groups:
            if group["name"] == "Customers":
                self.assertEqual(
                    group["policy_names"],
                    ["Read Customer"],
                    msg=values.MSG_CAT_GROUP_READ.format(
                        name="Customers", what="customer content only"
                    ),
                    abort_on_fail=False,
                )
            elif group["name"] != "Administrators":
                self.assertTrue(
                    {"Read Internal", "Read Customer"} <= set(group["policy_names"]),
                    msg=values.MSG_CAT_GROUP_READ.format(
                        name=group["name"], what="internal and customer content"
                    ),
                    abort_on_fail=False,
                )

    def bud_the_release_and_visions_migrations_freeze_the_catalogue(self):
        policies, groups = self.bloom.bloom_default_catalogue()
        by_name = {policy["name"]: policy for policy in policies}
        actions = self.bloom.bloom_resource_actions()
        values = self.parameters
        release = self.bloom.bloom_load_migration(values.CAT_RELEASE_MIGRATION)
        visions = self.bloom.bloom_load_migration(values.CAT_VISIONS_MIGRATION)
        expected = {policy["name"]: copy.deepcopy(policy) for policy in release.DEFAULT_POLICIES}
        for name in visions.COVERED_POLICIES:
            expected[name]["permissions"]["VIS"] = list(expected[name]["permissions"]["SPEC"])
            expected[name]["type_tags"]["VIS"] = dict(expected[name]["type_tags"]["SPEC"])
        expected[visions.VISIONS] = {
            "name": visions.VISIONS,
            "description": "",
            "scope": "document",
            "permissions": {"VIS": visions.VIS_ACTIONS},
            "type_tags": {"VIS": {"all": True, "visibility": [], "tags": []}},
        }
        self.assertEqual(by_name, expected, msg=values.MSG_CAT_FROZEN, abort_on_fail=False)
        release_groups = {group["name"]: copy.deepcopy(group) for group in release.DEFAULT_GROUPS}
        owners = release_groups[visions.PRODUCT_OWNERS]["policy_names"]
        owners.insert(owners.index("Specifications") + 1, visions.VISIONS)
        self.assertEqual(
            {group["name"]: group for group in groups},
            release_groups,
            msg=values.MSG_CAT_FROZEN_GROUPS,
            abort_on_fail=False,
        )
        maintainer_set = {
            policy["name"]
            for policy in release.DEFAULT_POLICIES
            if policy["scope"] in {"document", "project"}
            and policy["name"]
            not in {"Read Internal", "Read Customer", "Review Internal", "Review Customer"}
        }
        self.assertEqual(
            set(visions.RELEASED_MAINTAINER_SET),
            maintainer_set,
            msg=values.MSG_CAT_MAINTAINER_SET,
            abort_on_fail=False,
        )

    def bud_the_reviewer_policies_grant_only_review(self):
        policies, groups = self.bloom.bloom_default_catalogue()
        by_name = {policy["name"]: policy for policy in policies}
        actions = self.bloom.bloom_resource_actions()
        documents = self.bloom.bloom_permission_resources_of_documents()
        for name, origin in self.parameters.CAT_REVIEWERS:
            policy = by_name[name]
            self.assertEqual(
                (
                    policy["scope"],
                    policy["permissions"],
                    policy["type_tags"],
                    any(name in group["policy_names"] for group in groups),
                ),
                (
                    "project",
                    {resource: ["review"] for resource in documents},
                    {
                        resource: {
                            "all": origin is None,
                            "visibility": [origin] if origin else [],
                            "tags": [],
                        }
                        for resource in documents
                    },
                    False,
                ),
                msg=self.parameters.MSG_CAT_REVIEWER.format(name=name),
                abort_on_fail=False,
            )
