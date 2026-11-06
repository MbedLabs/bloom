"""
* @file     ${tests/api/jira_filter_validation.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the validation of an integration's Jira filter.
* @author   Amine El Omari
* @date     2026-11-06
* @version  1.0.0
* @note     Base class containing the bud methods of this module tests the validation of an integration's Jira filter.
"""

from tests.bloom_test_base import BloomTestCase


class JiraFilterValidationBase(BloomTestCase):

    def bud_valid_filter_is_accepted(self):
        error = self.bloom.bloom_try_validate_jira_filter(
            [self.parameters.BUG], {self.parameters.JIRA_HIGHEST: self.parameters.CRITICAL}
        )
        self.print_variables({"error": error})
        self.assertEqual(
            (error,), (None,), msg=self.parameters.MSG_FILTER_VALID, abort_on_fail=False
        )

    def bud_blank_issue_type_is_refused(self):
        error = self.bloom.bloom_try_validate_jira_filter([" "], None)
        self.print_variables({"error": error})
        self.assertEqual(
            (error or (None,))[0],
            self.parameters.STATUS_BAD_REQUEST,
            msg=self.parameters.MSG_FILTER_BLANK_TYPE,
            abort_on_fail=False,
        )

    def bud_map_to_an_unknown_level_is_refused_and_named(self):
        error = self.bloom.bloom_try_validate_jira_filter(
            None, {self.parameters.JIRA_HIGHEST: self.parameters.UNKNOWN_LEVEL}
        )
        self.print_variables({"error": error})
        self.assertIn(
            member=self.parameters.UNKNOWN_LEVEL,
            container=str((error or (None, ""))[1]),
            msg=self.parameters.MSG_FILTER_UNKNOWN_LEVEL,
            abort_on_fail=False,
        )
