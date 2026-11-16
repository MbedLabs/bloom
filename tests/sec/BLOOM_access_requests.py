"""
* @file     ${tests/sec/BLOOM_access_requests.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A refused user asks the administrators for access once per resource, and an administrator decides once.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the access request API with two administrators and one member.
"""

from tests.sec.access_requests import AccessRequestsBase


class AccessRequestsTest(AccessRequestsBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        password, kind, prefix = values.API_PASSWORD, values.ARQ_KIND, values.ARQ_PREFIX
        request, decide = bloom.bloom_api_request_access, bloom.bloom_api_decide_access_request
        events = bloom.bloom_list_audit_events
        bloom.bloom_start_full_api()
        sent = bloom.bloom_capture_access_request_mail()
        self.admin_id = bloom.bloom_add_admin(values.ARQ_BOSS_EMAIL, password)
        bloom.bloom_add_admin(values.ARQ_SECOND_EMAIL, password)
        self.member_id = bloom.bloom_add_account(
            values.ARQ_MEMBER_EMAIL, password, values.API_MEMBER_ROLE
        )
        member, _ = bloom.bloom_log_in(values.ARQ_MEMBER_EMAIL, password)
        admin, _ = bloom.bloom_log_in(values.ARQ_BOSS_EMAIL, password)

        self.first = request(member, kind, values.ARQ_REF, prefix)
        self.again = request(member, kind, values.ARQ_REF, prefix)
        self.mails = list(sent)
        self.requested_events = events(values.ARQ_REQUESTED_ACTION)

        self.mine_before = bloom.bloom_api_my_access_request(
            member, kind, values.ARQ_MINE_REF, prefix
        )
        mine = request(member, kind, values.ARQ_MINE_REF, prefix)
        self.mine_after = bloom.bloom_api_my_access_request(
            member, kind, values.ARQ_MINE_REF, prefix
        )
        self.unmailed = bloom.bloom_api_request_access_while_mail_fails(
            member, kind, values.ARQ_FAILED_MAIL_REF, prefix
        )
        self.pending_before = [answer.json()["id"] for answer in (self.first, mine, self.unmailed)]

        decided = request(member, kind, values.ARQ_DECIDED_REF, values.ARQ_DECIDED_PREFIX)
        decided_id = decided.json()["id"]
        self.listed = bloom.bloom_api_list_access_requests(admin, values.ARQ_DECIDED_PREFIX)
        self.member_decision = decide(member, decided_id, values.ARQ_GRANTED)
        self.granted = decide(admin, decided_id, values.ARQ_GRANTED)
        self.decided_twice = decide(admin, decided_id, values.ARQ_REFUSED)
        self.granted_events = events(values.ARQ_GRANTED_ACTION)

        other_prefix = values.ARQ_OTHER_PREFIX
        self.refusable = request(member, kind, values.ARQ_REFUSED_REF, other_prefix).json()["id"]
        self.other = request(member, kind, values.ARQ_PENDING_REF, other_prefix).json()["id"]
        self.member_list = bloom.bloom_api_list_all_access_requests(member)
        self.all = bloom.bloom_api_list_all_access_requests(admin)
        self.refused = decide(admin, self.refusable, values.ARQ_REFUSED)
        self.pending = bloom.bloom_api_list_all_access_requests(admin)
        self.history = bloom.bloom_api_list_all_access_requests(admin, values.ARQ_REFUSED)
        self.refused_twice = decide(admin, self.refusable, values.ARQ_GRANTED)
        self.refused_events = events(values.ARQ_REFUSED_ACTION)

        self.anonymous = request(None, kind, values.ARQ_REF, prefix)
        self.invalid = request(member, kind, values.ARQ_INVALID_REF, prefix)
        mails, records = len(sent), len(events(values.ARQ_REQUESTED_ACTION))
        self.admin_request = request(admin, kind, values.ARQ_ADMIN_REF, prefix)
        self.admin_silence = (
            len(sent) - mails,
            len(events(values.ARQ_REQUESTED_ACTION)) - records,
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    AccessRequestsTest().run()
