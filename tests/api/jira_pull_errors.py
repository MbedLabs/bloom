"""
* @file     ${tests/api/jira_pull_errors.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the errors Sync now reports.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests the errors Sync now reports.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class JiraPullErrorsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_pull_without_project_key_is_refused(self):
        _, error = self.bloom.bloom_try_sync_now(
            self.tc_env.setting_id, self.parameters.ADMIN_EMAIL
        )
        self.print_variables({"error": error})
        self.assertEqual(
            (error or (None,))[0],
            self.parameters.STATUS_BAD_REQUEST,
            msg=self.parameters.MSG_PULL_NEEDS_KEY,
            abort_on_fail=False,
        )

    def bud_pull_of_an_unknown_integration_is_not_found(self):
        _, error = self.bloom.bloom_try_sync_now(
            self.parameters.UNKNOWN_SETTING_ID, self.parameters.OTHER_ADMIN_EMAIL
        )
        self.print_variables({"error": error})
        self.assertEqual(
            (error or (None,))[0],
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_PULL_UNKNOWN,
            abort_on_fail=False,
        )

    def bud_refused_account_is_a_bad_request_naming_it(self):
        self.bloom.bloom_update_setting(
            self.tc_env.setting_id, jira_project_key=self.parameters.JIRA_PROJECT
        )
        self.bloom.bloom_refuse_with(self.parameters.STATUS_UNAUTHORIZED)
        _, error = self.bloom.bloom_try_sync_now(
            self.tc_env.setting_id, self.parameters.THIRD_ADMIN_EMAIL
        )
        self.print_variables({"error": error})
        found = error or (None, "")
        self.assertEqual(
            (found[0], str(found[1]).startswith(self.parameters.JIRA_REFUSED_ACCOUNT)),
            (self.parameters.STATUS_BAD_REQUEST, True),
            msg=self.parameters.MSG_PULL_REFUSED,
            abort_on_fail=False,
        )

    def bud_unreachable_jira_is_a_bad_gateway_naming_it(self):
        self.bloom.bloom_make_unreachable()
        _, error = self.bloom.bloom_try_sync_now(
            self.tc_env.setting_id, self.parameters.FOURTH_ADMIN_EMAIL
        )
        self.print_variables({"error": error})
        found = error or (None, "")
        self.assertEqual(
            (found[0], str(found[1]).startswith(self.parameters.JIRA_UNREACHABLE)),
            (self.parameters.STATUS_BAD_GATEWAY, True),
            msg=self.parameters.MSG_PULL_UNREACHABLE,
            abort_on_fail=False,
        )
