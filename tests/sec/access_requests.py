"""
* @file     ${tests/sec/access_requests.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the request a refused user sends the administrators for access.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the access requests.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class AccessRequestsBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_first_request_is_created_pending_with_its_mail_sent(self):
        self.print_variables({"status": self.first.status_code, "body": self.first.json()})
        body = self.first.json()
        self.assertEqual(
            (self.first.status_code, body["status"], body["mail_sent"]),
            (self.parameters.STATUS_CREATED, self.parameters.ARQ_PENDING, True),
            msg=self.parameters.MSG_ARQ_CREATED,
            abort_on_fail=False,
        )

    def bud_same_request_again_is_already_requested(self):
        self.print_variables({"status": self.again.status_code, "body": self.again.json()})
        body = self.again.json()
        self.assertEqual(
            (self.again.status_code, body["already_requested"], body["id"]),
            (self.parameters.STATUS_OK, True, self.first.json()["id"]),
            msg=self.parameters.MSG_ARQ_REPEATED,
            abort_on_fail=False,
        )

    def bud_request_mails_each_administrator_once(self):
        self.assertEqual(
            sorted(mail["to_email"] for mail in self.mails),
            sorted([self.parameters.ARQ_BOSS_EMAIL, self.parameters.ARQ_SECOND_EMAIL]),
            msg=self.parameters.MSG_ARQ_MAILED,
            abort_on_fail=False,
        )

    def bud_mail_names_the_requester_the_resource_and_the_review_page(self):
        mail = self.mails[0]
        self.print_variables({"mail": mail})
        self.assertEqual(
            (
                mail["requester_email"],
                mail["resource"],
                mail["project"],
                mail["review_link"].endswith(self.parameters.ARQ_REVIEW_LINK_END),
                mail["request_id"],
            ),
            (
                self.parameters.ARQ_MEMBER_EMAIL,
                self.parameters.ARQ_RESOURCE_LABEL,
                self.parameters.ARQ_PREFIX,
                True,
                self.first.headers["x-request-id"],
            ),
            msg=self.parameters.MSG_ARQ_MAIL,
            abort_on_fail=False,
        )

    def bud_request_is_recorded_once_with_its_resource(self):
        self.assertEqual(
            [(event.target_type, event.target_id) for event in self.requested_events],
            [(self.parameters.ARQ_KIND, self.parameters.ARQ_REF)],
            msg=self.parameters.MSG_ARQ_RECORDED,
            abort_on_fail=False,
        )

    def bud_answer_holds_the_requests_own_fields(self):
        self.assertEqual(
            sorted(self.first.json()),
            self.parameters.ARQ_FIELDS,
            msg=self.parameters.MSG_ARQ_FIELDS,
            abort_on_fail=False,
        )

    def bud_answer_names_no_requester_email_and_no_picture(self):
        body = self.first.json()
        self.assertEqual(
            (body["requester_email"], body["requester_profile_picture_url"]),
            (None, None),
            msg=self.parameters.MSG_ARQ_UNDISCLOSED,
            abort_on_fail=False,
        )

    def bud_page_learns_no_request_is_pending_before(self):
        self.assertEqual(
            (self.mine_before.status_code, self.mine_before.json()),
            (self.parameters.STATUS_OK, None),
            msg=self.parameters.MSG_ARQ_NONE_YET,
            abort_on_fail=False,
        )

    def bud_page_learns_the_request_is_pending_after(self):
        self.print_variables(
            {"status": self.mine_after.status_code, "body": self.mine_after.json()}
        )
        self.assertEqual(
            self.mine_after.json()["status"],
            self.parameters.ARQ_PENDING,
            msg=self.parameters.MSG_ARQ_MINE,
            abort_on_fail=False,
        )

    def bud_request_whose_mail_fails_is_created_and_says_so(self):
        self.print_variables({"status": self.unmailed.status_code, "body": self.unmailed.json()})
        self.assertEqual(
            (self.unmailed.status_code, self.unmailed.json()["mail_sent"]),
            (self.parameters.STATUS_CREATED, False),
            msg=self.parameters.MSG_ARQ_MAIL_FAILED,
            abort_on_fail=False,
        )

    def bud_administrator_lists_the_projects_request(self):
        self.print_variables({"status": self.listed.status_code, "body": self.listed.json()})
        self.assertEqual(
            [row["requester_email"] for row in self.listed.json()],
            [self.parameters.ARQ_MEMBER_EMAIL],
            msg=self.parameters.MSG_ARQ_LISTED,
            abort_on_fail=False,
        )

    def bud_members_decision_is_refused_403(self):
        self.print_variables(
            {"status": self.member_decision.status_code, "body": self.member_decision.json()}
        )
        self.assertEqual(
            self.member_decision.status_code,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_ARQ_MEMBER_DECISION,
            abort_on_fail=False,
        )

    def bud_administrators_grant_is_answered_as_granted(self):
        self.print_variables({"status": self.granted.status_code, "body": self.granted.json()})
        self.assertEqual(
            (self.granted.status_code, self.granted.json()["status"]),
            (self.parameters.STATUS_OK, self.parameters.ARQ_GRANTED),
            msg=self.parameters.MSG_ARQ_GRANT,
            abort_on_fail=False,
        )

    def bud_second_decision_is_refused_409(self):
        self.print_variables(
            {"status": self.decided_twice.status_code, "body": self.decided_twice.json()}
        )
        self.assertEqual(
            self.decided_twice.status_code,
            self.parameters.STATUS_CONFLICT,
            msg=self.parameters.MSG_ARQ_DECIDED_TWICE,
            abort_on_fail=False,
        )

    def bud_grant_is_recorded_with_the_administrator_and_the_requester(self):
        self.assertEqual(
            [
                (event.actor_user_id, event.details["requester_user_id"])
                for event in self.granted_events
            ],
            [(self.admin_id, self.member_id)],
            msg=self.parameters.MSG_ARQ_GRANT_RECORDED,
            abort_on_fail=False,
        )

    def bud_members_list_of_every_request_is_refused_403(self):
        self.print_variables(
            {"status": self.member_list.status_code, "body": self.member_list.json()}
        )
        self.assertEqual(
            self.member_list.status_code,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_ARQ_MEMBER_LIST,
            abort_on_fail=False,
        )

    def bud_administrator_lists_every_pending_request(self):
        self.assertEqual(
            (self.all.status_code, sorted(row["id"] for row in self.all.json())),
            (
                self.parameters.STATUS_OK,
                sorted(self.pending_before + [self.refusable, self.other]),
            ),
            msg=self.parameters.MSG_ARQ_ALL,
            abort_on_fail=False,
        )

    def bud_administrators_refusal_is_answered_as_refused(self):
        self.print_variables({"status": self.refused.status_code, "body": self.refused.json()})
        self.assertEqual(
            (self.refused.status_code, self.refused.json()["status"]),
            (self.parameters.STATUS_OK, self.parameters.ARQ_REFUSED),
            msg=self.parameters.MSG_ARQ_REFUSE,
            abort_on_fail=False,
        )

    def bud_refused_request_leaves_the_pending_list(self):
        self.assertEqual(
            sorted(row["id"] for row in self.pending.json()),
            sorted(self.pending_before + [self.other]),
            msg=self.parameters.MSG_ARQ_PENDING_LEFT,
            abort_on_fail=False,
        )

    def bud_refused_request_is_listed_under_refused(self):
        self.assertEqual(
            [row["id"] for row in self.history.json()],
            [self.refusable],
            msg=self.parameters.MSG_ARQ_HISTORY,
            abort_on_fail=False,
        )

    def bud_decision_on_a_refused_request_is_refused_409(self):
        self.print_variables(
            {"status": self.refused_twice.status_code, "body": self.refused_twice.json()}
        )
        self.assertEqual(
            self.refused_twice.status_code,
            self.parameters.STATUS_CONFLICT,
            msg=self.parameters.MSG_ARQ_DECIDED_TWICE,
            abort_on_fail=False,
        )

    def bud_refusal_is_recorded_with_the_administrator_and_the_requester(self):
        self.assertEqual(
            [
                (event.actor_user_id, event.details["requester_user_id"])
                for event in self.refused_events
            ],
            [(self.admin_id, self.member_id)],
            msg=self.parameters.MSG_ARQ_REFUSAL_RECORDED,
            abort_on_fail=False,
        )

    def bud_request_without_a_sign_in_is_refused_401(self):
        self.print_variables({"status": self.anonymous.status_code, "body": self.anonymous.json()})
        self.assertEqual(
            self.anonymous.status_code,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_ARQ_ANONYMOUS,
            abort_on_fail=False,
        )

    def bud_reference_with_path_characters_is_refused_422(self):
        self.print_variables({"status": self.invalid.status_code, "body": self.invalid.json()})
        self.assertEqual(
            self.invalid.status_code,
            self.parameters.STATUS_UNPROCESSABLE,
            msg=self.parameters.MSG_ARQ_INVALID,
            abort_on_fail=False,
        )

    def bud_administrators_own_request_is_refused_409(self):
        self.print_variables(
            {"status": self.admin_request.status_code, "body": self.admin_request.json()}
        )
        self.assertEqual(
            (
                self.admin_request.status_code,
                self.parameters.ARQ_NOTHING_PHRASE in self.admin_request.json()["detail"],
            ),
            (self.parameters.STATUS_CONFLICT, True),
            msg=self.parameters.MSG_ARQ_ADMIN,
            abort_on_fail=False,
        )

    def bud_administrators_own_request_mails_nobody_and_is_not_recorded(self):
        self.print_variables({"mails, records": self.admin_silence})
        self.assertEqual(
            self.admin_silence,
            (0, 0),
            msg=self.parameters.MSG_ARQ_ADMIN_SILENT,
            abort_on_fail=False,
        )
