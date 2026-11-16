"""
* @file     ${tests/logic/entitlements.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests project admission, group policies and their scopes.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the project entitlements.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class EntitlementsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_a_group_grant_reaches_only_its_project(self):
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_entitlement_user()
        values = self.parameters
        read = self.bloom.bloom_add_access_policy("Read", values.ENT_READ)
        self.bloom.bloom_add_team(seeded.user, seeded.project, [read])
        self.assertEqual(
            (
                self.bloom.bloom_can_access_project(seeded.user, seeded.project),
                self.bloom.bloom_can_access_project(seeded.user, seeded.other),
            ),
            (True, False),
            msg=values.MSG_ENT_GROUP_PROJECT,
            abort_on_fail=False,
        )

    def bud_no_grant_is_refused_403(self):
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_entitlement_user()
        values = self.parameters
        self.assertEqual(
            self.bloom.bloom_project_access_refusal(seeded.user, seeded.project),
            values.STATUS_FORBIDDEN,
            msg=values.MSG_ENT_NO_GRANT,
            abort_on_fail=False,
        )

    def bud_an_instance_administrator_needs_no_entry(self):
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_entitlement_user("admin")
        values = self.parameters
        self.assertTrue(
            self.bloom.bloom_can_access_project(seeded.user, seeded.project),
            msg=values.MSG_ENT_ADMIN,
            abort_on_fail=False,
        )

    def bud_a_membership_without_an_entry_grants_nothing(self):
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_entitlement_user()
        values = self.parameters
        self.bloom.bloom_add_membership_without_entry(seeded.user, seeded.project)
        self.assertEqual(
            self.bloom.bloom_can_access_project(seeded.user, seeded.project),
            False,
            msg=values.MSG_ENT_LEGACY,
            abort_on_fail=False,
        )

    def bud_leaving_a_group_keeps_the_direct_grant(self):
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_entitlement_user()
        values = self.parameters
        read = self.bloom.bloom_add_access_policy("Read", values.ENT_READ)
        write = self.bloom.bloom_add_access_policy("Write", values.ENT_EDIT)
        self.bloom.bloom_add_direct_access(seeded.user, seeded.project, [read])
        membership = self.bloom.bloom_add_team(seeded.user, seeded.project, [write])
        terms = self.bloom.bloom_access_term_permissions(seeded.user, seeded.project)
        self.print_variables({"terms": terms})
        self.assertEqual(
            any("edit" in term.get("REQ", ()) for term in terms),
            False,
            msg=values.MSG_ENT_SEPARATE,
            abort_on_fail=False,
        )
        self.bloom.bloom_remove_team_membership(membership)
        self.assertEqual(
            self.bloom.bloom_access_term_permissions(seeded.user, seeded.project),
            [{"REQ": {"view"}}],
            msg=values.MSG_ENT_DIRECT_KEPT,
            abort_on_fail=False,
        )

    def bud_a_broad_read_lends_no_visibility_to_a_scoped_write(self):
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_entitlement_user()
        values = self.parameters
        read = self.bloom.bloom_add_access_policy("Broad read", values.ENT_READ)
        write = self.bloom.bloom_add_access_policy(
            "Customer write", values.ENT_EDIT, "customer", ["REQ"]
        )
        self.bloom.bloom_add_team(seeded.user, seeded.project, [read, write])
        internal = self.bloom.bloom_add_requirement_row(seeded.project, *values.ENT_INTERNAL_ROW)
        customer = self.bloom.bloom_add_requirement_row(seeded.project, *values.ENT_CUSTOMER_ROW)
        self.assertEqual(
            (
                self.bloom.bloom_row_allows(seeded.user, internal, "view", "REQ"),
                self.bloom.bloom_row_allows(seeded.user, internal, "edit", "REQ"),
                self.bloom.bloom_row_allows(seeded.user, customer, "edit", "REQ"),
            ),
            (True, False, True),
            msg=values.MSG_ENT_BROAD_READ,
            abort_on_fail=False,
        )

    def bud_a_type_scope_keeps_its_link_permission(self):
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_entitlement_user()
        values = self.parameters
        policy = self.bloom.bloom_add_access_policy(
            "Requirement links", values.ENT_LINKS, types=["REQ"]
        )
        self.bloom.bloom_add_team(seeded.user, seeded.project, [policy])
        self.assertEqual(
            (
                self.bloom.bloom_project_access_refusal(
                    seeded.user, seeded.project, ("create", "link")
                ),
                self.bloom.bloom_project_access_refusal(seeded.user, seeded.project, ("view", "TC"))
                is not None,
            ),
            (None, True),
            msg=values.MSG_ENT_LINK,
            abort_on_fail=False,
        )

    def bud_external_grants_do_not_expose_parameters_403(self):
        for owner, how in ((False, "with a parameter policy"), (True, "who owns the project")):
            self.bloom.bloom_new_database()
            seeded = self.bloom.bloom_seed_entitlement_user("external")
            policies = (
                []
                if owner
                else [
                    self.bloom.bloom_add_access_policy(
                        "Parameter grant", self.parameters.ENT_PARAMETER
                    )
                ]
            )
            self.bloom.bloom_add_direct_access(seeded.user, seeded.project, policies, owner=owner)
            self.assertEqual(
                self.bloom.bloom_project_access_refusal(
                    seeded.user, seeded.project, ("view", "parameter")
                ),
                self.parameters.STATUS_FORBIDDEN,
                msg=self.parameters.MSG_ENT_EXTERNAL_PARAMETERS.format(how=how),
                abort_on_fail=False,
            )

    def bud_an_owner_entry_is_direct_and_keeps_the_instance_role(self):
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_entitlement_user()
        values = self.parameters
        self.bloom.bloom_add_direct_access(seeded.user, seeded.project, owner=True)
        terms = self.bloom.bloom_access_term_permissions(seeded.user, seeded.project)
        self.assertEqual(
            (
                self.bloom.bloom_can_access_project(seeded.user, seeded.project),
                self.bloom.bloom_can_access_project(seeded.user, seeded.other),
                self.bloom.bloom_role_of(seeded.user),
                any(term == {"*": {"*"}} for term in terms),
            ),
            (True, False, "maintainer", True),
            msg=values.MSG_ENT_OWNER,
            abort_on_fail=False,
        )

    def bud_a_customer_scope_does_not_change_the_account_identity(self):
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_entitlement_user()
        values = self.parameters
        policy = self.bloom.bloom_add_access_policy("Customer scope", values.ENT_READ, "customer")
        self.bloom.bloom_add_direct_access(seeded.user, seeded.project, [policy])
        external = self.bloom.bloom_add_external_account()
        self.bloom.bloom_add_direct_access(external, seeded.project, [policy])
        self.assertEqual(
            (
                self.bloom.bloom_is_customer_only(seeded.user, seeded.project),
                self.bloom.bloom_is_customer_only(external, seeded.project),
            ),
            (False, True),
            msg=values.MSG_ENT_IDENTITY,
            abort_on_fail=False,
        )

    def bud_an_external_account_reads_customer_rows_only(self):
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_entitlement_user("external")
        values = self.parameters
        policy = self.bloom.bloom_add_access_policy("Broad read", values.ENT_READ, "internal")
        self.bloom.bloom_add_direct_access(seeded.user, seeded.project, [policy])
        internal = self.bloom.bloom_add_requirement_row(seeded.project, *values.ENT_INTERNAL_ROW)
        customer = self.bloom.bloom_add_requirement_row(seeded.project, *values.ENT_CUSTOMER_ROW)
        self.assertEqual(
            (
                self.bloom.bloom_row_allows(seeded.user, internal, "view", "REQ"),
                self.bloom.bloom_row_allows(seeded.user, customer, "view", "REQ"),
                self.bloom.bloom_visible_requirement_ids(seeded.user, seeded.project),
            ),
            (False, True, [customer]),
            msg=values.MSG_ENT_EXTERNAL_READING,
            abort_on_fail=False,
        )

    def bud_approval_is_covered_only_where_the_approving_policy_reaches(self):
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_entitlement_user()
        values = self.parameters
        author = self.bloom.bloom_add_access_policy("Author", values.ENT_AUTHOR)
        signer = self.bloom.bloom_add_access_policy("Signer", values.ENT_SIGNER, "customer")
        self.bloom.bloom_add_direct_access(seeded.user, seeded.project, [author, signer])
        covered = lambda visibility, *action: self.bloom.bloom_creation_covered(
            seeded.user, seeded.project, "REQ", visibility, [], *action
        )
        self.assertEqual(
            (covered("internal"), covered("customer")),
            (True, True),
            msg=values.MSG_ENT_CREATION,
            abort_on_fail=False,
        )
        self.assertEqual(
            (covered("internal", "approve"), covered("customer", "approve")),
            (False, True),
            msg=values.MSG_ENT_APPROVAL,
            abort_on_fail=False,
        )

    def bud_a_write_grant_stays_within_its_resource_and_origin(self):
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_entitlement_user()
        values = self.parameters
        write = self.bloom.bloom_add_access_policy(
            "Customer author", values.ENT_EDIT, "customer", ["REQ"]
        )
        self.bloom.bloom_add_team(seeded.user, seeded.project, [write])
        internal = self.bloom.bloom_add_requirement_row(seeded.project, *values.ENT_INTERNAL_ROW)
        customer = self.bloom.bloom_add_requirement_row(seeded.project, *values.ENT_CUSTOMER_ROW)
        self.assertEqual(
            (
                self.bloom.bloom_row_allows(seeded.user, customer, "view", "REQ"),
                self.bloom.bloom_row_allows(seeded.user, customer, "edit", "REQ"),
                self.bloom.bloom_row_allows(seeded.user, customer, "approve", "REQ"),
                self.bloom.bloom_row_allows(seeded.user, customer, "delete", "REQ"),
                self.bloom.bloom_row_allows(seeded.user, internal, "view", "REQ"),
                self.bloom.bloom_row_allows(seeded.user, customer, "view", "TC"),
            ),
            (True, True, False, False, False, False),
            msg=values.MSG_ENT_WRITE_SCOPE,
            abort_on_fail=False,
        )

    def bud_overlapping_bundles_keep_their_origins_and_account_caps(self):
        values = self.parameters
        for role, who in (
            ("maintainer", "an internal account"),
            ("external", "an external account"),
        ):
            self.bloom.bloom_new_database()
            seeded = self.bloom.bloom_seed_entitlement_user(role)
            read = self.bloom.bloom_add_access_policy("Read all", values.ENT_READ)
            write = self.bloom.bloom_add_access_policy(
                "Customer author", values.ENT_CUSTOMER_AUTHOR, "customer"
            )
            self.bloom.bloom_add_policy_bundles(
                seeded.user, seeded.project, {"Readers": [read], "Authors": [write]}
            )
            internal = self.bloom.bloom_add_requirement_row(
                seeded.project, *values.ENT_INTERNAL_ROW
            )
            customer = self.bloom.bloom_add_requirement_row(
                seeded.project, *values.ENT_CUSTOMER_ROW
            )
            internal_account = role == "maintainer"
            self.assertEqual(
                (
                    self.bloom.bloom_row_allows(seeded.user, customer, "view", "REQ"),
                    self.bloom.bloom_row_allows(seeded.user, customer, "edit", "REQ"),
                    self.bloom.bloom_row_allows(seeded.user, internal, "edit", "REQ"),
                    self.bloom.bloom_can_access_project(seeded.user, seeded.other),
                ),
                (True, True, False, False),
                msg=values.MSG_ENT_BUNDLES.format(who=who),
                abort_on_fail=False,
            )
            self.assertEqual(
                (
                    self.bloom.bloom_row_allows(seeded.user, internal, "view", "REQ"),
                    self.bloom.bloom_row_allows(seeded.user, customer, "approve", "REQ"),
                    self.bloom.bloom_row_allows(seeded.user, customer, "delete", "REQ"),
                ),
                (internal_account, internal_account, internal_account),
                msg=values.MSG_ENT_BUNDLE_CAPS.format(
                    state="allowed" if internal_account else "refused", who=who
                ),
                abort_on_fail=False,
            )

    def bud_overlapping_bundles_do_not_borrow_a_tag_scope(self):
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_entitlement_user()
        values = self.parameters
        read = self.bloom.bloom_add_access_policy(
            "Unrestricted read", values.ENT_READ, type_tags={"REQ": {"all": True}}
        )
        write = self.bloom.bloom_add_access_policy(
            "Chosen tag write", values.ENT_EDIT, type_tags={"REQ": {"tags": [101]}}
        )
        self.bloom.bloom_add_policy_bundles(
            seeded.user, seeded.project, {"Readers": [read], "Authors": [write]}
        )
        covered = lambda tags, action: self.bloom.bloom_creation_covered(
            seeded.user, seeded.project, "REQ", "internal", tags, action
        )
        self.assertEqual(
            (covered([202], "view"), covered([202], "edit"), covered([101], "edit")),
            (True, False, True),
            msg=values.MSG_ENT_TAG_SCOPE,
            abort_on_fail=False,
        )
