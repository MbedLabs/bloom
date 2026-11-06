"""
* @file     ${tests/api/jira_webhook_forged_legacy.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests a forged delivery against a submitted change request.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests a forged delivery against a submitted change request.
"""

from tests.bloom_test_base import BloomTestCase


class JiraWebhookForgedLegacyBase(BloomTestCase):

    def bud_forged_delivery_is_refused_and_changes_nothing(self):
        status = self.bloom.bloom_get_change(self.tc_env.change_id).status
        found = (self.tc_response.status_code, status)
        self.print_variables({"answer, status": found})
        self.assertEqual(
            found,
            (self.parameters.STATUS_FORBIDDEN, self.parameters.CHANGE_SUBMITTED),
            msg=self.parameters.MSG_FORGED_LEGACY,
            abort_on_fail=False,
        )
