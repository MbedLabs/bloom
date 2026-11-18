"""
* @file     ${tests/logic/jira_inbound.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the mapping of Jira issues to Bloom.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the Jira inbound mapping.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class JiraInboundBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_atlassian_document_text_is_flattened(self):
        self.assertEqual(
            (
                self.bloom.bloom_adf_to_text(None),
                self.bloom.bloom_adf_to_text("  plain  "),
                self.bloom.bloom_adf_to_text(self.parameters.JIN_ADF),
                self.bloom.bloom_adf_to_text({"type": "text", "text": "loose"}),
            ),
            ("", "plain", "Found by PRJ-TC-004\nline one\n@Ada", "loose"),
            msg=self.parameters.MSG_JIN_TEXT,
            abort_on_fail=False,
        )

    def bud_the_filter_defaults_to_bugs_and_honours_the_label(self):
        values, setting = self.parameters, self.bloom.bloom_jira_setting
        self.assertEqual(
            (
                self.bloom.bloom_jira_issue_types(setting()),
                self.bloom.bloom_jira_filter(setting(), values.JIN_BUG),
                self.bloom.bloom_jira_filter(setting(), values.JIN_TASK),
                self.bloom.bloom_jira_filter(
                    setting(jira_issue_types=["bug", "Task"]), values.JIN_TASK
                ),
                self.bloom.bloom_jira_filter(setting(jira_label="bench"), values.JIN_BUG),
                self.bloom.bloom_jira_filter(setting(jira_label="field"), values.JIN_BUG),
            ),
            (["Bug"], True, False, True, True, False),
            msg=values.MSG_JIN_FILTER,
            abort_on_fail=False,
        )

    def bud_priorities_map_to_bloom_levels(self):
        setting, level = self.bloom.bloom_jira_setting, self.bloom.bloom_jira_level
        self.assertEqual(
            (
                level(setting(), {"priority": {"name": "Highest"}}),
                level(setting(), {"priority": {"name": "Lowest"}}),
                level(setting(), {}),
                level(setting(jira_priority_map={"Low": "High"}), {"priority": {"name": "Low"}}),
            ),
            ("Critical", "Low", "Medium", "High"),
            msg=self.parameters.MSG_JIN_PRIORITY,
            abort_on_fail=False,
        )

    def bud_an_issue_with_a_resolution_is_resolved(self):
        self.assertEqual(
            (
                self.bloom.bloom_jira_resolved({"resolution": {"name": "Fixed"}}),
                self.bloom.bloom_jira_resolved({"resolution": None}),
            ),
            (True, False),
            msg=self.parameters.MSG_JIN_RESOLVED,
            abort_on_fail=False,
        )

    def bud_referenced_test_cases_are_read(self):
        values, setting = self.parameters, self.bloom.bloom_jira_setting
        fields = {**values.JIN_REFERENCES, "description": values.JIN_ADF}
        self.assertEqual(
            (
                self.bloom.bloom_jira_references("PRJ", setting(), fields),
                self.bloom.bloom_jira_references(
                    "PRJ", setting(jira_reference_field=values.JIN_REFERENCE_FIELD), fields
                ),
            ),
            (["PRJ-TC-002", "PRJ-TC-004"], ["PRJ-TC-002", "PRJ-TC-004", "PRJ-TC-009"]),
            msg=values.MSG_JIN_REFERENCES,
            abort_on_fail=False,
        )

    def bud_the_jql_names_the_project_types_label_and_clause(self):
        values, setting = self.parameters, self.bloom.bloom_jira_setting
        full = setting(
            jira_issue_types=["Bug", 'Say "hi"'], jira_label="bench", jira_jql="priority = High"
        )
        self.assertEqual(
            (self.bloom.bloom_jira_jql(full), self.bloom.bloom_jira_jql(setting())),
            (values.JIN_JQL_FULL, values.JIN_JQL_DEFAULT),
            msg=values.MSG_JIN_JQL,
            abort_on_fail=False,
        )

    def bud_the_search_fields_and_issue_link(self):
        values, setting = self.parameters, self.bloom.bloom_jira_setting
        self.assertEqual(
            (
                self.bloom.bloom_jira_search_fields(
                    setting(jira_reference_field=values.JIN_REFERENCE_FIELD)
                )[-1],
                self.bloom.bloom_jira_issue_url(setting(), "PROJ-7"),
                self.bloom.bloom_jira_issue_url(setting(base_url=None), "PROJ-7"),
            ),
            (values.JIN_REFERENCE_FIELD, values.JIN_URL, None),
            msg=values.MSG_JIN_FIELDS,
            abort_on_fail=False,
        )
