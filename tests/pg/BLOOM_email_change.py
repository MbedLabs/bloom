"""
* @file     ${tests/pg/BLOOM_email_change.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An email changes only after the right mailboxes confirm, ends the sessions, and an invitation verifies the address.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the application on a new PostgreSQL database with one account per way of changing an email.
"""

from tests.pg.email_change import EmailChangeBase


class EmailChangeTest(EmailChangeBase):

    def setUpClass(self):
        super().setUpClass()
        self.tc_postgres = self.bloom.bloom_use_postgres()
        if not self.tc_postgres:
            return
        bloom, values = self.bloom, self.parameters
        password, role = values.API_PASSWORD, values.SESSION_ROLE
        log_in, account, token_of = (
            bloom.bloom_log_in_for_cookie,
            bloom.bloom_read_account,
            bloom.bloom_mail_token,
        )
        bloom.bloom_start_main_api()
        bloom.bloom_add_admin(values.ADMIN_EMAIL, password)
        admin = log_in(values.ADMIN_EMAIL, password).access_token

        old, new = values.EMAIL_SELF_OLD, values.EMAIL_SELF_NEW
        bloom.bloom_add_account(old, password, values.EMAIL_ADMIN_ROLE)
        login = log_in(old, password)
        self.tc_self_request = bloom.bloom_request_email_change(login.access_token, password, new)
        self.tc_self_pending = account(login.access_token)
        self.tc_self_authorized = bloom.bloom_confirm_email_change(
            token_of(self.tc_self_request.mails[0])
        )
        self.tc_self_waiting = account(login.access_token)
        self.tc_self_confirmed = bloom.bloom_confirm_email_change(
            token_of(self.tc_self_authorized.mails[0])
        )
        self.tc_self_after = bloom.bloom_probe_email_sessions(login, old, new, password)

        old, new = values.EMAIL_MEMBER_OLD, values.EMAIL_MEMBER_NEW
        member = bloom.bloom_add_account(old, password, role)
        login = log_in(old, password)
        self.tc_member_request = bloom.bloom_request_email_change(login.access_token, password, new)
        self.tc_member_pending = account(login.access_token)
        self.tc_member_approved = bloom.bloom_approve_email_change(admin, member)
        self.tc_member_waiting = account(login.access_token)
        self.tc_member_not_yet = (log_in(new, password).status, log_in(old, password).status)
        self.tc_member_confirmed = bloom.bloom_confirm_email_change(
            token_of(self.tc_member_approved.mails[0])
        )
        self.tc_member_after = bloom.bloom_probe_email_sessions(login, old, new, password)
        self.tc_member_account = account(log_in(new, password).access_token)

        old, approved, other = (
            values.EMAIL_STALE_OLD,
            values.EMAIL_STALE_APPROVED,
            values.EMAIL_STALE_OTHER,
        )
        member = bloom.bloom_add_account(old, password, role)
        bloom.bloom_request_email_change(log_in(old, password).access_token, password, approved)
        stale = token_of(bloom.bloom_approve_email_change(admin, member).mails[0])
        bloom.bloom_set_pending_email(member, other)
        self.tc_stale_confirmed = bloom.bloom_confirm_email_change(stale)
        self.tc_stale_logins = tuple(
            log_in(email, password).status for email in (old, approved, other)
        )

        bloom.bloom_add_account(values.EMAIL_GUARD, password, role)
        login = log_in(values.EMAIL_GUARD, password)
        self.tc_guard_request = bloom.bloom_request_email_change(
            login.access_token, values.HTTP_WRONG_PASSWORD, values.EMAIL_GUARD_NEW
        )
        self.tc_guard_account = account(login.access_token)

        old, new = values.EMAIL_ADMIN_OLD, values.EMAIL_ADMIN_NEW
        member = bloom.bloom_add_account(old, password, role)
        self.tc_admin_bypass = bloom.bloom_update_account_email(admin, member, new)
        self.tc_admin_started = bloom.bloom_start_email_change_for(admin, member, new)
        self.tc_admin_confirmed = bloom.bloom_confirm_email_change(
            token_of(self.tc_admin_started.mails[0])
        )
        self.tc_admin_logins = (log_in(old, password).status, log_in(new, password).status)

        invited = bloom.bloom_send_invitation(admin, values.EMAIL_INVITED, role)
        self.tc_invite_accepted = bloom.bloom_accept_invitation(
            token_of(invited.mails[0]), password
        )
        login = log_in(values.EMAIL_INVITED, password)
        self.tc_invite_login = login.status
        self.tc_invite_account = account(login.access_token)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    EmailChangeTest().run()
