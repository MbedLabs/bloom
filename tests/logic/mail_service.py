"""
* @file     ${tests/logic/mail_service.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests sending mail and the content of each Bloom mail.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the mail service.
"""

import re

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class MailServiceBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_mail_is_sent_with_the_fixed_sender_name(self):
        values = self.parameters
        sent = self.bloom.bloom_send_through_smtp(values.MLS_SMTP, values.MLS_MESSAGE).server
        self.assertEqual(
            (
                sent.host,
                sent.port,
                sent.timeout,
                sent.started_tls,
                sent.logged_in,
                len(sent.messages),
            ),
            ("smtp.example.com", 587, 9, True, ("smtp-user", "smtp-password"), 1),
            msg=values.MSG_MLS_SERVER,
            abort_on_fail=False,
        )
        self.assertEqual(
            sent.messages[0]["From"],
            values.MLS_SENDER,
            msg=values.MSG_MLS_SENDER,
            abort_on_fail=False,
        )

    def bud_a_refused_starttls_reports_where_and_why(self):
        values = self.parameters
        relay = {**values.MLS_RELAY, "SMTP_STARTTLS": True}
        error = self.bloom.bloom_send_through_smtp(
            relay, values.MLS_SHORT_MESSAGE, server="no_starttls"
        ).error
        self.print_variables({"error": error})
        for word in values.MLS_STARTTLS_REPORT:
            self.assertIn(
                word,
                error or "",
                msg=values.MSG_MLS_STARTTLS.format(word=word),
                abort_on_fail=False,
            )

    def bud_a_delivery_error_is_a_configuration_error(self):
        self.assertTrue(
            self.bloom.bloom_delivery_error_is_a_configuration_error(),
            msg=self.parameters.MSG_MLS_SUBCLASS,
            abort_on_fail=False,
        )

    def bud_an_unreachable_relay_is_reported(self):
        values = self.parameters
        error = self.bloom.bloom_send_through_smtp(
            values.MLS_RELAY, values.MLS_SHORT_MESSAGE, server="unreachable"
        ).error
        self.assertIn("mail:2525", error or "", msg=values.MSG_MLS_UNREACHABLE, abort_on_fail=False)

    def bud_the_delivery_log_leaves_out_message_and_recipient(self):
        values = self.parameters
        log = self.bloom.bloom_send_through_smtp(values.MLS_RELAY, values.MLS_PRIVATE_MESSAGE).log
        self.print_variables({"log": log})
        self.assertIn("Email sent", log, msg=values.MSG_MLS_LOG_SENT, abort_on_fail=False)
        for word in values.MLS_PRIVATE_WORDS:
            self.assertNotIn(
                word, log, msg=values.MSG_MLS_LOG_PRIVATE.format(word=word), abort_on_fail=False
            )

    def bud_the_error_log_leaves_out_the_server_response(self):
        values = self.parameters
        failed = self.bloom.bloom_send_through_smtp(
            values.MLS_RELAY, values.MLS_PRIVATE_MESSAGE, server="refuses"
        )
        self.print_variables({"log": failed.log})
        self.assertEqual(
            ("SMTPException" in failed.log, "remote response" in (failed.error or "")),
            (True, True),
            msg=values.MSG_MLS_LOG_ERROR,
            abort_on_fail=False,
        )
        for word in values.MLS_SERVER_WORDS:
            self.assertNotIn(
                word,
                failed.log,
                msg=values.MSG_MLS_LOG_SERVER.format(word=word),
                abort_on_fail=False,
            )

    def bud_a_workflow_request_mail_matches_in_html_and_text(self):
        values = self.parameters
        mails = self.bloom.bloom_capture_mail("send_workflow_request_email", **values.MLS_WORKFLOW)
        mail = mails[0]
        self.assertEqual(
            (len(mails), mail["subject"], mail["to"]),
            (1, values.MLS_WORKFLOW["event_title"], values.MLS_WORKFLOW["to_email"]),
            msg=values.MSG_MLS_WORKFLOW_HEAD,
            abort_on_fail=False,
        )
        for word in values.MLS_WORKFLOW_TEXT:
            self.assertIn(
                word,
                mail["text"],
                msg=values.MSG_MLS_WORKFLOW_TEXT.format(word=word),
                abort_on_fail=False,
            )
        for word in values.MLS_WORKFLOW_HTML:
            self.assertIn(
                word,
                mail["html"],
                msg=values.MSG_MLS_WORKFLOW_HTML.format(word=word),
                abort_on_fail=False,
            )
        self.assertEqual(
            (
                "<script>" in mail["html"],
                mail["html"].count("<a href="),
                "${" in mail["html"] + mail["text"],
                mail["text"].startswith(values.MLS_TEXT_HEAD),
            ),
            (False, 1, False, True),
            msg=values.MSG_MLS_WORKFLOW_SAFE,
            abort_on_fail=False,
        )

    def bud_an_access_request_mail_has_matching_next_steps(self):
        values = self.parameters
        mail = self.bloom.bloom_capture_mail("send_access_request_email", **values.MLS_ACCESS)[0]
        self.assertEqual(
            (
                mail["subject"],
                ">Bloom PLM by EmbedLabs</h1>" in mail["html"],
                mail["text"].startswith(values.MLS_TEXT_HEAD),
                values.MLS_ACCESS_NEXT in mail["html"],
                values.MLS_ACCESS_NEXT in mail["text"],
                mail["html"].count("<a href="),
            ),
            (values.MLS_ACCESS_SUBJECT, True, True, True, True, 1),
            msg=values.MSG_MLS_ACCESS,
            abort_on_fail=False,
        )
        self.assertEqual(
            ("Writer &lt;script&gt;" in mail["html"], "Writer <script>" in mail["text"]),
            (True, True),
            msg=values.MSG_MLS_ACCESS_ESCAPED,
            abort_on_fail=False,
        )

    def bud_every_mail_follows_the_product_structure(self):
        values = self.parameters
        mails = [
            (self.bloom.bloom_capture_mail(sender, **fields), sender)
            for sender, fields in values.MLS_EVERY_MAIL
        ]
        self.assertEqual(
            sum(len(sent) for sent, _ in mails),
            8,
            msg=values.MSG_MLS_EVERY_COUNT,
            abort_on_fail=False,
        )
        for sent, sender in mails:
            html, text = sent[0]["html"], sent[0]["text"]
            self.assertEqual(
                (
                    "<title>Bloom PLM by EmbedLabs</title>" in html,
                    bool(re.search(values.MLS_HEADING, html)),
                    html.count("<a href="),
                    values.MLS_LINK in html,
                    values.MLS_LINK in text,
                    "Bloom PLM" in text,
                    values.MLS_HTML_RIGHTS in html,
                    values.MLS_TEXT_RIGHTS in text,
                    "EmbedLabs Bloom" in html + text + sent[0]["subject"],
                    "${" in html + text,
                ),
                (True, True, 1, True, True, True, True, True, False, False),
                msg=values.MSG_MLS_EVERY.format(sender=sender),
                abort_on_fail=False,
            )
