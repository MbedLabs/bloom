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
        self.postgres = self.bloom.bloom_use_postgres()
        if not self.postgres:
            return
        bloom, values = self.bloom, self.parameters
        password, role = values.API_PASSWORD, values.SESSION_ROLE
        log_in = bloom.bloom_log_in_for_cookie
        bloom.bloom_start_main_api()
        bloom.bloom_add_admin(values.ADMIN_EMAIL, password)
        self.admin = log_in(values.ADMIN_EMAIL, password).access_token

        bloom.bloom_add_account(values.EMAIL_SELF_OLD, password, values.EMAIL_ADMIN_ROLE)
        self.self_login = log_in(values.EMAIL_SELF_OLD, password)
        self.self_request = bloom.bloom_request_email_change(
            self.self_login.access_token, password, values.EMAIL_SELF_NEW
        )

        self.member_id = bloom.bloom_add_account(values.EMAIL_MEMBER_OLD, password, role)
        self.member_login = log_in(values.EMAIL_MEMBER_OLD, password)
        self.member_request = bloom.bloom_request_email_change(
            self.member_login.access_token, password, values.EMAIL_MEMBER_NEW
        )

        stale = bloom.bloom_add_account(values.EMAIL_STALE_OLD, password, role)
        bloom.bloom_request_email_change(
            log_in(values.EMAIL_STALE_OLD, password).access_token,
            password,
            values.EMAIL_STALE_APPROVED,
        )
        approval = bloom.bloom_approve_email_change(self.admin, stale)
        self.stale_token = bloom.bloom_mail_token(approval.mails[0])
        bloom.bloom_set_pending_email(stale, values.EMAIL_STALE_OTHER)

        bloom.bloom_add_account(values.EMAIL_GUARD, password, role)
        self.guard_login = log_in(values.EMAIL_GUARD, password)

        self.admin_member = bloom.bloom_add_account(values.EMAIL_ADMIN_OLD, password, role)

        self.invitation = bloom.bloom_send_invitation(self.admin, values.EMAIL_INVITED, role)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    EmailChangeTest().run()
