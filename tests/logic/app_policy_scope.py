"""
* @file     ${tests/logic/app_policy_scope.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that group app rules and admitted project content keep separate scopes.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the app policy scope.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class AppPolicyScopeBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_group_app_rules_apply_without_project_admission(self):
        self.bloom.bloom_new_database()
        result = self.bloom.bloom_app_scope_case()
        self.print_variables({"app terms": result.app_terms, "app": result.app})
        self.assertEqual(
            (result.app_terms, result.app, result.project_terms),
            (self.parameters.APS_APP_RESOURCES, self.parameters.APS_APP_PERMISSIONS, ()),
            msg=self.parameters.MSG_APS_APP,
            abort_on_fail=False,
        )

    def bud_other_policy_scopes_supply_no_app_terms(self):
        for scope in ("document", "project"):
            self.bloom.bloom_new_database()
            result = self.bloom.bloom_app_scope_case(scope=scope)
            self.assertEqual(
                result.app_terms,
                [],
                msg=self.parameters.MSG_APS_SCOPE.format(scope=scope),
                abort_on_fail=False,
            )

    def bud_admitted_content_rules_never_include_app_resources(self):
        self.bloom.bloom_new_database()
        result = self.bloom.bloom_app_scope_case(admission="group")
        self.print_variables({"project": result.project})
        self.assertEqual(
            result.project,
            self.parameters.APS_ADMITTED,
            msg=self.parameters.MSG_APS_ADMITTED,
            abort_on_fail=False,
        )

    def bud_a_project_replacement_keeps_the_app_rules(self):
        self.bloom.bloom_new_database()
        result = self.bloom.bloom_app_scope_case(admission="replacement")
        self.assertEqual(
            (result.project, result.app),
            (self.parameters.APS_REPLACED, self.parameters.APS_APP_PERMISSIONS),
            msg=self.parameters.MSG_APS_REPLACED,
            abort_on_fail=False,
        )

    def bud_app_rules_do_not_open_admin_only_management(self):
        self.bloom.bloom_new_database()
        result = self.bloom.bloom_app_scope_case()
        self.assertEqual(
            (result.app["users"], result.admin_only),
            ({"view", "create", "edit"}, self.parameters.STATUS_FORBIDDEN),
            msg=self.parameters.MSG_APS_ADMIN_ONLY,
            abort_on_fail=False,
        )

    def bud_an_instance_administrator_holds_every_permission(self):
        self.bloom.bloom_new_database()
        self.assertEqual(
            self.bloom.bloom_admin_permissions(),
            {"*": {"*"}},
            msg=self.parameters.MSG_APS_ADMIN,
            abort_on_fail=False,
        )

    def bud_direct_bundles_combine_without_indirect_project_rights(self):
        self.bloom.bloom_new_database()
        result = self.bloom.bloom_app_scope_case(admission="bundles")
        self.print_variables({"project": result.project})
        self.assertEqual(
            (result.project, "project" in result.project, result.app["access"]),
            (self.parameters.APS_BUNDLES, False, {"delete"}),
            msg=self.parameters.MSG_APS_BUNDLES,
            abort_on_fail=False,
        )
