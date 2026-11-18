"""
* @file     ${tests/logic/import_markdown_formatting.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that imported Markdown becomes the editor's rich content and that a declaration sets the kind.
* @author   Amine El Omari
* @date     2026-11-18
* @version  1.0.0
* @note     Base class containing the bud methods of the formatted Markdown import.
"""

import re

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ImportMarkdownFormattingBase(BloomTestCase):

    interface = BloomLogicInterface

    def _import(self, document, actions=None):
        self.bloom.bloom_new_database()
        self.records = self.bloom.bloom_seed_markdown_project()
        return self.bloom.bloom_import_markdown(
            self.records.project, self.records.admin, document, actions
        )

    def _import_more(self, document):
        return self.bloom.bloom_import_markdown(self.records.project, self.records.admin, document)

    def _parts(self, title):
        return self.bloom.bloom_rich_content_parts(self.bloom.bloom_imported_contents().get(title))

    def _sign_in(self):
        values = self.parameters
        result, refusal = self._import(values.MDF_SIGN_IN)
        specification = self.bloom.bloom_artefact_titled("Document", values.MDF_SIGN_IN_TITLE)
        requirements = [
            self.bloom.bloom_artefact_titled("Requirement", title)
            for title in (values.MDF_REFUSAL_RULE, values.MDF_IDLE_RULE)
        ]
        return result or refusal, specification, requirements

    def bud_an_imported_specification_has_rich_content(self):
        values = self.parameters
        self._import(values.MDF_SIGN_IN)
        nodes, _, _, text = self._parts(values.MDF_SIGN_IN_TITLE)
        self.print_variables({"nodes": sorted(map(str, nodes)), "text": text})
        self.assertEqual(
            (values.MDF_SPECIFICATION_NODES <= nodes, text.startswith(values.MDF_SIGN_IN_OPENING)),
            (True, True),
            msg=values.MSG_MDF_SPECIFICATION,
            abort_on_fail=False,
        )

    def bud_a_specification_mentions_the_requirements_of_its_document(self):
        values = self.parameters
        _, specification, requirements = self._sign_in()
        mentions = self.bloom.bloom_artefact_mentions(
            specification.content_json if specification else None
        )
        self.print_variables({"mentions": mentions})
        self.assertEqual(
            mentions,
            [f"REQ:{requirement.id}" for requirement in requirements if requirement],
            msg=values.MSG_MDF_SPEC_MENTIONS,
            abort_on_fail=False,
        )

    def bud_each_mention_links_the_specification(self):
        values = self.parameters
        _, specification, requirements = self._sign_in()
        links = self.bloom.bloom_artefact_links("SPEC", specification.id) if specification else []
        self.print_variables({"links": links})
        self.assertEqual(
            links,
            sorted(
                ("REQ", requirement.id, values.MDF_LINK_ROLE)
                for requirement in requirements
                if requirement
            ),
            msg=values.MSG_MDF_SPEC_LINKS,
            abort_on_fail=False,
        )

    def bud_the_description_names_each_mention_by_its_id(self):
        values = self.parameters
        _, specification, requirements = self._sign_in()
        description = (specification.description or "") if specification else ""
        named = [f"#{requirement.req_id}" in description for requirement in requirements]
        self.print_variables({"description": description})
        self.assertEqual(
            (named, "[[" in description),
            ([True, True], False),
            msg=values.MSG_MDF_SPEC_DESCRIPTION,
            abort_on_fail=False,
        )

    def bud_linked_artefacts_get_no_unlinked_notice(self):
        values = self.parameters
        result, _, _ = self._sign_in()
        notes = self.bloom.bloom_notification_bodies()
        self.print_variables({"notifications": notes})
        self.assertEqual(
            (getattr(result, "notifications_created", None), notes),
            (0, []),
            msg=values.MSG_MDF_NO_UNLINKED_NOTICE,
            abort_on_fail=False,
        )

    def bud_an_existing_requirement_is_mentioned_by_its_title(self):
        values = self.parameters
        self._import(values.MDF_EXISTING_REQUIREMENT)
        requirement = self.bloom.bloom_artefact_titled("Requirement", values.MDF_EXISTING_RULE)
        self._import_more(values.MDF_EXISTING_SPECIFICATION)
        specification = self.bloom.bloom_artefact_titled(
            "Document", values.MDF_EXISTING_SPECIFICATION_TITLE
        )
        found = (
            self.bloom.bloom_artefact_mentions(specification.content_json),
            self.bloom.bloom_artefact_links("SPEC", specification.id),
        )
        self.print_variables({"mentions, links": found})
        self.assertEqual(
            found,
            ([f"REQ:{requirement.id}"], [("REQ", requirement.id, values.MDF_LINK_ROLE)]),
            msg=values.MSG_MDF_EXISTING_MENTION,
            abort_on_fail=False,
        )

    def bud_the_format_examples_hold_no_id_and_specs_mention_requirements(self):
        values = self.parameters
        examples = self.bloom.bloom_import_format_examples()
        with_id = [example for example in examples if re.search(values.MDF_DOCUMENT_ID, example)]
        specs = [example for example in examples if "## [SPEC]" in example]
        self.print_variables({"examples": len(examples), "with an ID": with_id})
        self.assertEqual(
            (with_id, bool(specs), all("[[" in example for example in specs)),
            ([], True, True),
            msg=values.MSG_MDF_DOC_EXAMPLES,
            abort_on_fail=False,
        )

    def bud_an_unknown_or_ambiguous_title_stays_text(self):
        values = self.parameters
        result, refusal = self._import(values.MDF_UNMATCHED)
        specification = self.bloom.bloom_artefact_titled("Document", "Session overview")
        _, _, _, text = self.bloom.bloom_rich_content_parts(specification.content_json)
        errors = getattr(result, "errors", refusal) or []
        found = (
            [f"[[{title}]]" in text for title in (values.MDF_UNKNOWN_TITLE, values.MDF_TWIN_TITLE)],
            [
                any(title in error for error in errors)
                for title in (values.MDF_UNKNOWN_TITLE, values.MDF_TWIN_TITLE)
            ],
            self.bloom.bloom_artefact_links("SPEC", specification.id),
        )
        self.print_variables({"text": text, "errors": errors})
        self.assertEqual(
            found,
            ([True, True], [True, True], []),
            msg=values.MSG_MDF_UNMATCHED,
            abort_on_fail=False,
        )

    def bud_every_markdown_element_becomes_its_editor_node(self):
        values = self.parameters
        result, refusal = self._import(values.MDF_EVERY_ELEMENT)
        nodes, marks, _, text = self._parts(values.MDF_EVERY_ELEMENT_TITLE)
        sections = (
            {section.title: section.type_code for section in result.sections} if result else refusal
        )
        self.print_variables(
            {
                "sections": sections,
                "missing nodes": sorted(values.MDF_ELEMENT_NODES - nodes),
                "missing marks": sorted(values.MDF_ELEMENT_MARKS - marks),
                "text": text,
            }
        )
        self.assertEqual(
            (
                sections,
                sorted(values.MDF_ELEMENT_NODES - nodes),
                sorted(values.MDF_ELEMENT_MARKS - marks),
                "# not a heading" in text,
            ),
            (values.MDF_EVERY_ELEMENT_SECTIONS, [], [], True),
            msg=values.MSG_MDF_ELEMENTS,
            abort_on_fail=False,
        )

    def bud_a_parameter_reference_becomes_the_parameter_chip(self):
        values = self.parameters
        self._import(values.MDF_PARAMETER_REFERENCE)
        _, _, chips, text = self._parts(values.MDF_PARAMETER_REFERENCE_TITLE)
        self.print_variables({"chips": chips, "text": text})
        self.assertEqual(
            (chips, "{{" in text),
            (values.MDF_PARAMETER_CHIPS, False),
            msg=values.MSG_MDF_CHIPS,
            abort_on_fail=False,
        )

    def bud_a_test_case_keeps_its_rows_and_gets_rich_text(self):
        values = self.parameters
        self._import(values.MDF_TEST_CASE)
        case = self.bloom.bloom_test_case_titled("Relay boot")
        _, marks, _, text = self._parts("Relay boot")
        rows = [
            (row["row_type"], row["description"], row["expected_result"])
            for row in case.steps or []
        ]
        self.print_variables({"rows": rows, "marks": sorted(map(str, marks)), "text": text})
        self.assertEqual(
            (rows, "bold" in marks, text),
            (values.MDI_STEP_ROWS, True, values.MDF_TEST_CASE_TEXT),
            msg=values.MSG_MDF_TEST_CASE,
            abort_on_fail=False,
        )

    def bud_each_rich_type_holds_rich_content_and_the_others_plain_text(self):
        values = self.parameters
        self._import(values.MDF_EVERY_TYPE)
        contents = self.bloom.bloom_imported_contents()
        for title in values.MDF_EVERY_TYPE_TITLES:
            _, marks, _, text = self.bloom.bloom_rich_content_parts(contents.get(title))
            self.assertEqual(
                ("bold" in marks, text),
                (True, values.MDF_TYPED_TEXT),
                msg=values.MSG_MDF_EVERY_TYPE.format(title=title),
                abort_on_fail=False,
            )
        for kind, title in values.MDF_PLAIN_TYPES:
            row = self.bloom.bloom_artefact_titled(kind, title)
            found = (
                getattr(row, "content_json", None),
                getattr(row, "content_html", None),
                getattr(row, "description", None),
            )
            self.print_variables({title: found})
            self.assertEqual(
                found,
                (None, None, values.MDF_PLAIN_BODY),
                msg=values.MSG_MDF_PLAIN.format(title=title),
                abort_on_fail=False,
            )

    def bud_the_requirements_of_a_specification_stay_plain_text(self):
        values = self.parameters
        _, _, requirements = self._sign_in()
        found = (
            [(row.content_json, row.content_html) for row in requirements if row],
            "{{IDLE_MINUTES}}" in (requirements[1].description or "") if requirements[1] else None,
            self.bloom.bloom_project_variable_kinds().get("IDLE_MINUTES"),
        )
        self.print_variables({"rich content, idle reference, kind": found})
        self.assertEqual(
            found,
            ([(None, None), (None, None)], True, "parameter"),
            msg=values.MSG_MDF_SIGN_IN_REQUIREMENTS,
            abort_on_fail=False,
        )

    def bud_a_declaration_sets_the_kind(self):
        values = self.parameters
        self._import(values.MDF_TWO_KINDS)
        requirement = self.bloom.bloom_artefact_titled("Requirement", "Two kinds")
        kinds = self.bloom.bloom_project_variable_kinds()
        self.print_variables({"kinds": kinds})
        self.assertEqual(
            (kinds, requirement.description if requirement else None),
            (values.MDF_TWO_KINDS_VALUES, values.MDF_TWO_KINDS_TEXT),
            msg=values.MSG_MDF_KINDS,
            abort_on_fail=False,
        )

    def bud_a_declared_variable_collides_like_a_parameter_409(self):
        values = self.parameters
        _, refusal = self._import(values.MDF_VARIABLE_COLLISION)
        self.print_variables({"refusal": refusal})
        self.assertEqual(
            (refusal[0], refusal[1]["collisions"]) if refusal else None,
            (values.STATUS_CONFLICT, values.MDF_VARIABLE_COLLISION_FOUND),
            msg=values.MSG_MDF_VARIABLE_COLLISION,
            abort_on_fail=False,
        )
