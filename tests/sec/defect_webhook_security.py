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
        unsigned = self.bloom.bloom_post_github_webhook(self.body)
        self.print_variables({"status": unsigned.status, "body": unsigned.body})
        self.assertEqual(
            unsigned.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_HOOK_UNSIGNED,
            abort_on_fail=False,
        )

    def bud_github_delivery_with_a_wrong_signature_is_refused_403(self):
        wrong = self.bloom.bloom_post_github_webhook(
            self.body, signature=self.parameters.HOOK_WRONG_SIGNATURE
        )
        self.print_variables({"status": wrong.status, "body": wrong.body})
        self.assertEqual(
            wrong.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_HOOK_WRONG,
            abort_on_fail=False,
        )

    def bud_signed_github_delivery_without_a_delivery_id_is_refused_400(self):
        no_delivery = self.bloom.bloom_post_github_webhook(
            self.body, signature=self.bloom.bloom_sign(self.body)
        )
        self.print_variables({"status": no_delivery.status, "body": no_delivery.body})
        self.assertEqual(
            no_delivery.status,
            self.parameters.STATUS_BAD_REQUEST,
            msg=self.parameters.MSG_HOOK_NO_DELIVERY,
            abort_on_fail=False,
        )

    def bud_signed_github_delivery_over_1_mib_is_refused_413(self):
        body = self.bloom.bloom_oversized_webhook_body()
        oversized = self.bloom.bloom_post_github_webhook(
            body, self.bloom.bloom_sign(body), self.parameters.HOOK_OVERSIZED_DELIVERY
        )
        self.print_variables({"status": oversized.status, "body": oversized.body})
        self.assertEqual(
            oversized.status,
            self.parameters.STATUS_TOO_LARGE,
            msg=self.parameters.MSG_HOOK_OVERSIZED,
            abort_on_fail=False,
        )

    def bud_refused_deliveries_leave_the_defect_open(self):
        status_after_refusals = self.bloom.bloom_get_defect(self.github).status
        self.print_variables({"status": status_after_refusals})
        self.assertEqual(
            status_after_refusals,
            self.parameters.DEFECT_OPEN,
            msg=self.parameters.MSG_HOOK_UNCHANGED,
            abort_on_fail=False,
        )

    def bud_refused_deliveries_record_no_successful_sync(self):
        successes_after_refusals = [
            event.id for event in self.bloom.bloom_list_defect_events() if event.success
        ]
        self.print_variables({"successes": successes_after_refusals})
        self.assertEqual(
            successes_after_refusals,
            [],
            msg=self.parameters.MSG_HOOK_NO_EVENT,
            abort_on_fail=False,
        )

    def bud_signed_github_delivery_is_processed_200(self):
        valid = self.bloom.bloom_post_github_webhook(
            self.body, self.bloom.bloom_sign(self.body), self.parameters.HOOK_DELIVERY
        )
        self.print_variables({"status": valid.status, "body": valid.body})
        self.assertEqual(
            (valid.status, valid.body[self.parameters.HOOK_STATUS_KEY]),
            (self.parameters.STATUS_OK, self.parameters.HOOK_PROCESSED),
            msg=self.parameters.MSG_HOOK_PROCESSED,
            abort_on_fail=False,
        )

    def bud_processed_delivery_closes_the_defect(self):
        status_after_valid = self.bloom.bloom_get_defect(self.github).status
        self.print_variables({"status": status_after_valid})
        self.assertEqual(
            status_after_valid,
            self.parameters.DEFECT_CLOSED,
            msg=self.parameters.MSG_HOOK_CLOSED,
            abort_on_fail=False,
        )

    def bud_same_delivery_again_is_a_duplicate(self):
        replay = self.bloom.bloom_post_github_webhook(
            self.body, self.bloom.bloom_sign(self.body), self.parameters.HOOK_DELIVERY
        )
        self.print_variables({"body": replay.body})
        self.assertEqual(
            replay.body[self.parameters.HOOK_STATUS_KEY],
            self.parameters.HOOK_DUPLICATE,
            msg=self.parameters.MSG_HOOK_REPLAY,
            abort_on_fail=False,
        )

    def bud_gitlab_delivery_without_the_token_is_refused_403(self):
        gitlab_unsigned = self.bloom.bloom_post_gitlab_webhook(
            self.parameters.HOOK_GITLAB_NUMBER, self.parameters.REPO
        )
        self.print_variables({"status": gitlab_unsigned.status, "body": gitlab_unsigned.body})
        self.assertEqual(
            gitlab_unsigned.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_HOOK_GITLAB_UNSIGNED,
            abort_on_fail=False,
        )

    def bud_refused_gitlab_delivery_leaves_the_defect_open(self):
        gitlab_status = self.bloom.bloom_get_defect(self.gitlab).status
        self.print_variables({"status": gitlab_status})
        self.assertEqual(
            gitlab_status,
            self.parameters.DEFECT_OPEN,
            msg=self.parameters.MSG_HOOK_GITLAB_UNCHANGED,
            abort_on_fail=False,
        )

    def bud_gitlab_delivery_with_the_token_is_processed_200(self):
        gitlab_valid = self.bloom.bloom_post_gitlab_webhook(
            self.parameters.HOOK_GITLAB_NUMBER,
            self.parameters.REPO,
            self.parameters.WEBHOOK_SECRET,
            self.parameters.HOOK_GITLAB_DELIVERY,
        )
        self.print_variables({"status": gitlab_valid.status, "body": gitlab_valid.body})
        self.assertEqual(
            (
                gitlab_valid.status,
                gitlab_valid.body[self.parameters.HOOK_STATUS_KEY],
            ),
            (self.parameters.STATUS_OK, self.parameters.HOOK_PROCESSED),
            msg=self.parameters.MSG_HOOK_GITLAB_PROCESSED,
            abort_on_fail=False,
        )
