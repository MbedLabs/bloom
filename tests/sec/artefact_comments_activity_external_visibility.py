"""
* @file     ${tests/sec/artefact_comments_activity_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which requirements' comments and activity an external reader gets.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the comments and activity an external reader reads.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ArtefactCommentsActivityExternalVisibilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_comments_of_an_internal_requirement_are_hidden_404(self):
        hidden_comments = self.bloom.bloom_api_comments(
            self.reader.headers, self.parameters.READER_REQUIREMENT_KIND, self.internal
        )
        self.print_variables({"status": hidden_comments.status, "body": hidden_comments.body})
        self.assertEqual(
            hidden_comments.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_READER_COMMENTS_HIDDEN,
            abort_on_fail=False,
        )

    def bud_activity_of_an_internal_requirement_is_hidden_404(self):
        hidden_activity = self.bloom.bloom_api_activity(
            self.reader.headers, self.parameters.READER_REQUIREMENT_KIND, self.internal
        )
        self.print_variables({"status": hidden_activity.status, "body": hidden_activity.body})
        self.assertEqual(
            hidden_activity.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_READER_ACTIVITY_HIDDEN,
            abort_on_fail=False,
        )

    def bud_comments_of_a_customer_requirement_are_shown(self):
        comments = self.bloom.bloom_api_comments(
            self.reader.headers, self.parameters.READER_REQUIREMENT_KIND, self.customer
        )
        self.print_variables({"status": comments.status, "body": comments.body})
        self.assertEqual(
            (comments.status, [item["body"] for item in comments.body]),
            (self.parameters.STATUS_OK, [self.parameters.READER_VISIBLE_COMMENT]),
            msg=self.parameters.MSG_READER_COMMENTS_SHOWN,
            abort_on_fail=False,
        )

    def bud_activity_of_a_customer_requirement_is_shown(self):
        activity = self.bloom.bloom_api_activity(
            self.reader.headers, self.parameters.READER_REQUIREMENT_KIND, self.customer
        )
        self.print_variables({"status": activity.status, "body": activity.body})
        self.assertEqual(
            (activity.status, [item["summary"] for item in activity.body]),
            (self.parameters.STATUS_OK, [self.parameters.READER_VISIBLE_ACTIVITY]),
            msg=self.parameters.MSG_READER_ACTIVITY_SHOWN,
            abort_on_fail=False,
        )
