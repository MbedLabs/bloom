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
        self.print_variables(
            {"status": self.tc_hidden_comments.status, "body": self.tc_hidden_comments.body}
        )
        self.assertEqual(
            self.tc_hidden_comments.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_READER_COMMENTS_HIDDEN,
            abort_on_fail=False,
        )

    def bud_activity_of_an_internal_requirement_is_hidden_404(self):
        self.print_variables(
            {"status": self.tc_hidden_activity.status, "body": self.tc_hidden_activity.body}
        )
        self.assertEqual(
            self.tc_hidden_activity.status,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_READER_ACTIVITY_HIDDEN,
            abort_on_fail=False,
        )

    def bud_comments_of_a_customer_requirement_are_shown(self):
        self.print_variables({"status": self.tc_comments.status, "body": self.tc_comments.body})
        self.assertEqual(
            (self.tc_comments.status, [item["body"] for item in self.tc_comments.body]),
            (self.parameters.STATUS_OK, [self.parameters.READER_VISIBLE_COMMENT]),
            msg=self.parameters.MSG_READER_COMMENTS_SHOWN,
            abort_on_fail=False,
        )

    def bud_activity_of_a_customer_requirement_is_shown(self):
        self.print_variables({"status": self.tc_activity.status, "body": self.tc_activity.body})
        self.assertEqual(
            (self.tc_activity.status, [item["summary"] for item in self.tc_activity.body]),
            (self.parameters.STATUS_OK, [self.parameters.READER_VISIBLE_ACTIVITY]),
            msg=self.parameters.MSG_READER_ACTIVITY_SHOWN,
            abort_on_fail=False,
        )
