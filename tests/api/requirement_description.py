"""
* @file     ${tests/api/requirement_description.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the requirement description through the requirements API.
* @author   Amine El Omari
* @date     2026-11-14
* @version  1.0.0
* @note     Base class containing the bud methods of the requirement description.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class RequirementDescriptionBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_requirements_are_created(self):
        statuses = [answer.status for answer in self.created]
        self.print_variables({"statuses": statuses})
        self._equal(
            statuses,
            [self.parameters.STATUS_CREATED] * len(statuses),
            self.parameters.MSG_DESCRIPTION_CREATED,
        )

    def bud_editor_content_on_create_becomes_the_description(self):
        self.print_variables({"created": self.from_body})
        self._equal(
            self.from_body,
            self.parameters.DESCRIPTION_FROM_BODY,
            self.parameters.MSG_DESCRIPTION_FROM_BODY,
        )

    def bud_detail_holds_the_description(self):
        self.print_variables({"detail": self.detail})
        self._equal(
            self.detail,
            self.parameters.DESCRIPTION_FROM_BODY,
            self.parameters.MSG_DESCRIPTION_DETAIL,
        )

    def bud_editor_content_on_edit_follows_the_description(self):
        self.print_variables({"edited": self.edited})
        self._equal(
            self.edited,
            (self.parameters.STATUS_OK, *self.parameters.DESCRIPTION_AFTER_EDIT),
            self.parameters.MSG_DESCRIPTION_EDIT,
        )

    def bud_tag_in_a_new_description_creates_a_link(self):
        self.print_variables({"links": self.tagged_links})
        self._equal(
            self.tagged_links,
            [self.expected_link],
            self.parameters.MSG_DESCRIPTION_TAG_CREATE,
        )

    def bud_tag_added_on_edit_creates_a_link(self):
        self.print_variables({"before": self.untagged_links, "after": self.retagged_links})
        self._equal(self.untagged_links, [], self.parameters.MSG_DESCRIPTION_NO_TAG)
        self._equal(
            self.retagged_links,
            (self.parameters.STATUS_OK, [self.expected_link]),
            self.parameters.MSG_DESCRIPTION_TAG_EDIT,
        )

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
