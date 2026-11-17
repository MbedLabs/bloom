"""
* @file     ${tests/logic/requirement_text.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that a requirement holds its text as a plain description.
* @author   Amine El Omari
* @date     2026-11-14
* @version  1.0.0
* @note     Base class containing the bud methods of the requirement text conversion.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class RequirementTextBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_editor_content_becomes_plain_text(self):
        for (content_json, content_html), expected in self.parameters.TEXT_PLAIN_CASES:
            found = self.bloom.bloom_plain_text(content_json, content_html)
            self.print_variables({"html": content_html, "found": found, "expected": expected})
            self._equal(found, expected, self.parameters.MSG_TEXT_PLAIN)

    def bud_text_fills_or_follows_the_description(self):
        for arguments, expected in self.parameters.TEXT_DESCRIPTION_CASES:
            found = self.bloom.bloom_description_with_content(*arguments)
            self.print_variables({"arguments": arguments, "found": found, "expected": expected})
            self._equal(found, expected, self.parameters.MSG_TEXT_DESCRIPTION)

    def bud_reqif_import_counts(self):
        self.print_variables({"counts": self.import_counts})
        self._equal(
            self.import_counts, self.parameters.REQIF_COUNTS, self.parameters.MSG_REQIF_COUNTS
        )

    def bud_reqif_text_becomes_the_description(self):
        self.print_variables({"login": self.imported[1]})
        self._equal(self.imported[1], self.parameters.REQIF_LOGIN, self.parameters.MSG_REQIF_LOGIN)

    def bud_reqif_heading_object_is_imported(self):
        system = self.imported[0]
        found = (system[0], system[1], system[-1])
        self.print_variables({"system": found})
        self._equal(found, self.parameters.REQIF_SYSTEM_SOURCE, self.parameters.MSG_REQIF_SYSTEM)

    def bud_reqif_relation_becomes_one_refines_link(self):
        ids = dict(self.bloom.bloom_requirement_rows(("req_id", "id"), self.project_id))
        import_ids = (
            ids[self.parameters.REQIF_LOGIN[0]],
            ids[self.parameters.REQIF_SYSTEM_SOURCE[0]],
        )
        import_links = self.bloom.bloom_list_link_ends()
        legacy_links = self.bloom.bloom_count_requirement_links()
        self.print_variables({"links": import_links, "ids": import_ids})
        login_id, system_id = import_ids
        self._equal(
            import_links,
            [(login_id, system_id, *self.parameters.REQIF_LINK)],
            self.parameters.MSG_REQIF_LINK,
        )
        self._equal(
            legacy_links,
            self.parameters.REQIF_NO_REQUIREMENT_LINKS,
            self.parameters.MSG_REQIF_LEGACY,
        )

    def bud_copied_requirement_keeps_no_editor_content(self):
        self.bloom.bloom_copy_requirements(self.source_id, self.target_id)
        copied = self.bloom.bloom_requirement_rows(
            ("req_id", "title", "description", "content_json", "content_html"), self.target_id
        )
        self.print_variables({"copied": copied})
        self._equal(copied, self.parameters.TEXT_COPY_EXPECTED, self.parameters.MSG_TEXT_COPY)

    def _equal(self, actual, expected, message):
        """Assert the actual value equals the expected one."""
        self.assertEqual(actual, expected, msg=message, abort_on_fail=False)
