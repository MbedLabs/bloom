"""
* @file     ${tests/sec/defect_webhook_security.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests what a tracker delivery must carry before it changes a defect.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the defect webhook security.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class DefectWebhookSecurityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_github_delivery_without_a_signature_is_refused_403(self):
        self.print_variables({"status": self.unsigned.status, "body": self.unsigned.body})
        self.assertEqual(
            self.unsigned.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_HOOK_UNSIGNED,
            abort_on_fail=False,
        )

    def bud_github_delivery_with_a_wrong_signature_is_refused_403(self):
        self.print_variables({"status": self.wrong.status, "body": self.wrong.body})
        self.assertEqual(
            self.wrong.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_HOOK_WRONG,
            abort_on_fail=False,
        )

    def bud_signed_github_delivery_without_a_delivery_id_is_refused_400(self):
        self.print_variables({"status": self.no_delivery.status, "body": self.no_delivery.body})
        self.assertEqual(
            self.no_delivery.status,
            self.parameters.STATUS_BAD_REQUEST,
            msg=self.parameters.MSG_HOOK_NO_DELIVERY,
            abort_on_fail=False,
        )

    def bud_signed_github_delivery_over_1_mib_is_refused_413(self):
        self.print_variables({"status": self.oversized.status, "body": self.oversized.body})
        self.assertEqual(
            self.oversized.status,
            self.parameters.STATUS_TOO_LARGE,
            msg=self.parameters.MSG_HOOK_OVERSIZED,
            abort_on_fail=False,
        )

    def bud_refused_deliveries_leave_the_defect_open(self):
        self.assertEqual(
            self.status_after_refusals,
            self.parameters.DEFECT_OPEN,
            msg=self.parameters.MSG_HOOK_UNCHANGED,
            abort_on_fail=False,
        )

    def bud_refused_deliveries_record_no_successful_sync(self):
        self.assertEqual(
            self.successes_after_refusals,
            [],
            msg=self.parameters.MSG_HOOK_NO_EVENT,
            abort_on_fail=False,
        )

    def bud_signed_github_delivery_is_processed_200(self):
        self.print_variables({"status": self.valid.status, "body": self.valid.body})
        self.assertEqual(
            (self.valid.status, self.valid.body[self.parameters.HOOK_STATUS_KEY]),
            (self.parameters.STATUS_OK, self.parameters.HOOK_PROCESSED),
            msg=self.parameters.MSG_HOOK_PROCESSED,
            abort_on_fail=False,
        )

    def bud_processed_delivery_closes_the_defect(self):
        self.assertEqual(
            self.status_after_valid,
            self.parameters.DEFECT_CLOSED,
            msg=self.parameters.MSG_HOOK_CLOSED,
            abort_on_fail=False,
        )

    def bud_same_delivery_again_is_a_duplicate(self):
        self.print_variables({"body": self.replay.body})
        self.assertEqual(
            self.replay.body[self.parameters.HOOK_STATUS_KEY],
            self.parameters.HOOK_DUPLICATE,
            msg=self.parameters.MSG_HOOK_REPLAY,
            abort_on_fail=False,
        )

    def bud_gitlab_delivery_without_the_token_is_refused_403(self):
        self.print_variables(
            {"status": self.gitlab_unsigned.status, "body": self.gitlab_unsigned.body}
        )
        self.assertEqual(
            self.gitlab_unsigned.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_HOOK_GITLAB_UNSIGNED,
            abort_on_fail=False,
        )

    def bud_refused_gitlab_delivery_leaves_the_defect_open(self):
        self.assertEqual(
            self.gitlab_status,
            self.parameters.DEFECT_OPEN,
            msg=self.parameters.MSG_HOOK_GITLAB_UNCHANGED,
            abort_on_fail=False,
        )

    def bud_gitlab_delivery_with_the_token_is_processed_200(self):
        self.print_variables({"status": self.gitlab_valid.status, "body": self.gitlab_valid.body})
        self.assertEqual(
            (
                self.gitlab_valid.status,
                self.gitlab_valid.body[self.parameters.HOOK_STATUS_KEY],
            ),
            (self.parameters.STATUS_OK, self.parameters.HOOK_PROCESSED),
            msg=self.parameters.MSG_HOOK_GITLAB_PROCESSED,
            abort_on_fail=False,
        )
