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
        again = self.bloom.bloom_api_request_access(
            self.member,
            self.parameters.ARQ_KIND,
            self.parameters.ARQ_REF,
            self.parameters.ARQ_PREFIX,
        )
        self.print_variables({"status": again.status_code, "body": again.json()})
        body = again.json()
        self.assertEqual(
            (again.status_code, body["already_requested"], body["id"]),
            (self.parameters.STATUS_OK, True, self.first.json()["id"]),
            msg=self.parameters.MSG_ARQ_REPEATED,
            abort_on_fail=False,
        )

    def bud_request_mails_each_administrator_once(self):
        mails = list(self.sent)
        self.print_variables({"mails": [mail["to_email"] for mail in mails]})
        self.assertEqual(
            sorted(mail["to_email"] for mail in mails),
            sorted([self.parameters.ARQ_BOSS_EMAIL, self.parameters.ARQ_SECOND_EMAIL]),
            msg=self.parameters.MSG_ARQ_MAILED,
            abort_on_fail=False,
        )

    def bud_mail_names_the_requester_the_resource_and_the_review_page(self):
        mail = self.sent[0]
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
        requested_events = self.bloom.bloom_list_audit_events(self.parameters.ARQ_REQUESTED_ACTION)
        targets = [(event.target_type, event.target_id) for event in requested_events]
        self.print_variables({"targets": targets})
        self.assertEqual(
            targets,
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
        mine_before = self.bloom.bloom_api_my_access_request(
            self.member,
            self.parameters.ARQ_KIND,
            self.parameters.ARQ_MINE_REF,
            self.parameters.ARQ_PREFIX,
        )
        self.print_variables({"status": mine_before.status_code, "body": mine_before.json()})
        self.assertEqual(
            (mine_before.status_code, mine_before.json()),
            (self.parameters.STATUS_OK, None),
            msg=self.parameters.MSG_ARQ_NONE_YET,
            abort_on_fail=False,
        )

    def bud_page_learns_the_request_is_pending_after(self):
        values = self.parameters
        mine = self.bloom.bloom_api_request_access(
            self.member, values.ARQ_KIND, values.ARQ_MINE_REF, values.ARQ_PREFIX
        )
        self.mine_id = mine.json()["id"]
        mine_after = self.bloom.bloom_api_my_access_request(
            self.member, values.ARQ_KIND, values.ARQ_MINE_REF, values.ARQ_PREFIX
        )
        self.print_variables({"status": mine_after.status_code, "body": mine_after.json()})
        self.assertEqual(
            mine_after.json()["status"],
            self.parameters.ARQ_PENDING,
            msg=self.parameters.MSG_ARQ_MINE,
            abort_on_fail=False,
        )

    def bud_request_whose_mail_fails_is_created_and_says_so(self):
        unmailed = self.bloom.bloom_api_request_access_while_mail_fails(
            self.member,
            self.parameters.ARQ_KIND,
            self.parameters.ARQ_FAILED_MAIL_REF,
            self.parameters.ARQ_PREFIX,
        )
        self.unmailed_id = unmailed.json()["id"]
        self.print_variables({"status": unmailed.status_code, "body": unmailed.json()})
        self.assertEqual(
            (unmailed.status_code, unmailed.json()["mail_sent"]),
            (self.parameters.STATUS_CREATED, False),
            msg=self.parameters.MSG_ARQ_MAIL_FAILED,
            abort_on_fail=False,
        )

    def bud_administrator_lists_the_projects_request(self):
        values = self.parameters
        decided = self.bloom.bloom_api_request_access(
            self.member, values.ARQ_KIND, values.ARQ_DECIDED_REF, values.ARQ_DECIDED_PREFIX
        )
        self.decided_id = decided.json()["id"]
        listed = self.bloom.bloom_api_list_access_requests(self.admin, values.ARQ_DECIDED_PREFIX)
        self.print_variables({"status": listed.status_code, "body": listed.json()})
        self.assertEqual(
            [row["requester_email"] for row in listed.json()],
            [self.parameters.ARQ_MEMBER_EMAIL],
            msg=self.parameters.MSG_ARQ_LISTED,
            abort_on_fail=False,
        )

    def bud_members_decision_is_refused_403(self):
        member_decision = self.bloom.bloom_api_decide_access_request(
            self.member, self.decided_id, self.parameters.ARQ_GRANTED
        )
        self.print_variables(
            {"status": member_decision.status_code, "body": member_decision.json()}
        )
        self.assertEqual(
            member_decision.status_code,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_ARQ_MEMBER_DECISION,
            abort_on_fail=False,
        )

    def bud_administrators_grant_is_answered_as_granted(self):
        granted = self.bloom.bloom_api_decide_access_request(
            self.admin, self.decided_id, self.parameters.ARQ_GRANTED
        )
        self.print_variables({"status": granted.status_code, "body": granted.json()})
        self.assertEqual(
            (granted.status_code, granted.json()["status"]),
            (self.parameters.STATUS_OK, self.parameters.ARQ_GRANTED),
            msg=self.parameters.MSG_ARQ_GRANT,
            abort_on_fail=False,
        )

    def bud_second_decision_is_refused_409(self):
        decided_twice = self.bloom.bloom_api_decide_access_request(
            self.admin, self.decided_id, self.parameters.ARQ_REFUSED
        )
        self.print_variables({"status": decided_twice.status_code, "body": decided_twice.json()})
        self.assertEqual(
            decided_twice.status_code,
            self.parameters.STATUS_CONFLICT,
            msg=self.parameters.MSG_ARQ_DECIDED_TWICE,
            abort_on_fail=False,
        )

    def bud_grant_is_recorded_with_the_administrator_and_the_requester(self):
        granted_events = self.bloom.bloom_list_audit_events(self.parameters.ARQ_GRANTED_ACTION)
        actors = [
            (event.actor_user_id, event.details["requester_user_id"]) for event in granted_events
        ]
        self.print_variables({"administrator, requester": actors})
        self.assertEqual(
            actors,
            [(self.admin_id, self.member_id)],
            msg=self.parameters.MSG_ARQ_GRANT_RECORDED,
            abort_on_fail=False,
        )

    def bud_members_list_of_every_request_is_refused_403(self):
        member_list = self.bloom.bloom_api_list_all_access_requests(self.member)
        self.print_variables({"status": member_list.status_code, "body": member_list.json()})
        self.assertEqual(
            member_list.status_code,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_ARQ_MEMBER_LIST,
            abort_on_fail=False,
        )

    def bud_administrator_lists_every_pending_request(self):
        values = self.parameters
        self.refusable = self.bloom.bloom_api_request_access(
            self.member, values.ARQ_KIND, values.ARQ_REFUSED_REF, values.ARQ_OTHER_PREFIX
        ).json()["id"]
        self.other = self.bloom.bloom_api_request_access(
            self.member, values.ARQ_KIND, values.ARQ_PENDING_REF, values.ARQ_OTHER_PREFIX
        ).json()["id"]
        every = self.bloom.bloom_api_list_all_access_requests(self.admin)
        pending_before = [self.first.json()["id"], self.mine_id, self.unmailed_id]
        self.print_variables({"status": every.status_code, "body": every.json()})
        self.assertEqual(
            (every.status_code, sorted(row["id"] for row in every.json())),
            (
                self.parameters.STATUS_OK,
                sorted(pending_before + [self.refusable, self.other]),
            ),
            msg=self.parameters.MSG_ARQ_ALL,
            abort_on_fail=False,
        )

    def bud_administrators_refusal_is_answered_as_refused(self):
        refused = self.bloom.bloom_api_decide_access_request(
            self.admin, self.refusable, self.parameters.ARQ_REFUSED
        )
        self.print_variables({"status": refused.status_code, "body": refused.json()})
        self.assertEqual(
            (refused.status_code, refused.json()["status"]),
            (self.parameters.STATUS_OK, self.parameters.ARQ_REFUSED),
            msg=self.parameters.MSG_ARQ_REFUSE,
            abort_on_fail=False,
        )

    def bud_refused_request_leaves_the_pending_list(self):
        pending = self.bloom.bloom_api_list_all_access_requests(self.admin)
        pending_before = [self.first.json()["id"], self.mine_id, self.unmailed_id]
        self.print_variables({"status": pending.status_code, "body": pending.json()})
        self.assertEqual(
            sorted(row["id"] for row in pending.json()),
            sorted(pending_before + [self.other]),
            msg=self.parameters.MSG_ARQ_PENDING_LEFT,
            abort_on_fail=False,
        )

    def bud_refused_request_is_listed_under_refused(self):
        history = self.bloom.bloom_api_list_all_access_requests(
            self.admin, self.parameters.ARQ_REFUSED
        )
        self.print_variables({"status": history.status_code, "body": history.json()})
        self.assertEqual(
            [row["id"] for row in history.json()],
            [self.refusable],
            msg=self.parameters.MSG_ARQ_HISTORY,
            abort_on_fail=False,
        )

    def bud_decision_on_a_refused_request_is_refused_409(self):
        refused_twice = self.bloom.bloom_api_decide_access_request(
            self.admin, self.refusable, self.parameters.ARQ_GRANTED
        )
        self.print_variables({"status": refused_twice.status_code, "body": refused_twice.json()})
        self.assertEqual(
            refused_twice.status_code,
            self.parameters.STATUS_CONFLICT,
            msg=self.parameters.MSG_ARQ_DECIDED_TWICE,
            abort_on_fail=False,
        )

    def bud_refusal_is_recorded_with_the_administrator_and_the_requester(self):
        refused_events = self.bloom.bloom_list_audit_events(self.parameters.ARQ_REFUSED_ACTION)
        actors = [
            (event.actor_user_id, event.details["requester_user_id"]) for event in refused_events
        ]
        self.print_variables({"administrator, requester": actors})
        self.assertEqual(
            actors,
            [(self.admin_id, self.member_id)],
            msg=self.parameters.MSG_ARQ_REFUSAL_RECORDED,
            abort_on_fail=False,
        )

    def bud_request_without_a_sign_in_is_refused_401(self):
        anonymous = self.bloom.bloom_api_request_access(
            None, self.parameters.ARQ_KIND, self.parameters.ARQ_REF, self.parameters.ARQ_PREFIX
        )
        self.print_variables({"status": anonymous.status_code, "body": anonymous.json()})
        self.assertEqual(
            anonymous.status_code,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_ARQ_ANONYMOUS,
            abort_on_fail=False,
        )

    def bud_reference_with_path_characters_is_refused_422(self):
        invalid = self.bloom.bloom_api_request_access(
            self.member,
            self.parameters.ARQ_KIND,
            self.parameters.ARQ_INVALID_REF,
            self.parameters.ARQ_PREFIX,
        )
        self.print_variables({"status": invalid.status_code, "body": invalid.json()})
        self.assertEqual(
            invalid.status_code,
            self.parameters.STATUS_UNPROCESSABLE,
            msg=self.parameters.MSG_ARQ_INVALID,
            abort_on_fail=False,
        )

    def bud_administrators_own_request_is_refused_409(self):
        values = self.parameters
        self.counts_before_admin_request = (
            len(self.sent),
            len(self.bloom.bloom_list_audit_events(values.ARQ_REQUESTED_ACTION)),
        )
        admin_request = self.bloom.bloom_api_request_access(
            self.admin, values.ARQ_KIND, values.ARQ_ADMIN_REF, values.ARQ_PREFIX
        )
        self.print_variables({"status": admin_request.status_code, "body": admin_request.json()})
        self.assertEqual(
            (
                admin_request.status_code,
                self.parameters.ARQ_NOTHING_PHRASE in admin_request.json()["detail"],
            ),
            (self.parameters.STATUS_CONFLICT, True),
            msg=self.parameters.MSG_ARQ_ADMIN,
            abort_on_fail=False,
        )

    def bud_administrators_own_request_mails_nobody_and_is_not_recorded(self):
        mails, records = self.counts_before_admin_request
        admin_silence = (
            len(self.sent) - mails,
            len(self.bloom.bloom_list_audit_events(self.parameters.ARQ_REQUESTED_ACTION)) - records,
        )
        self.print_variables({"mails, records": admin_silence})
        self.assertEqual(
            admin_silence,
            (0, 0),
            msg=self.parameters.MSG_ARQ_ADMIN_SILENT,
            abort_on_fail=False,
        )
