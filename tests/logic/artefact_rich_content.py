"""
* @file     ${tests/logic/artefact_rich_content.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that every editable artefact schema keeps its rich content.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the rich content schemas.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ArtefactRichContentBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_schemas_carry_rich_content_fields(self):
        for schema, fields in self.tc_fields.items():
            self.print_variables({"schema": schema, "fields": fields})
            for field in self.parameters.RICH_FIELDS:
                self.assertIn(
                    field,
                    fields,
                    msg=f"{self.parameters.MSG_RICH_FIELD}: {schema}",
                    abort_on_fail=False,
                )

    def bud_create_schemas_accept_an_editor_payload(self):
        for schema, built in self.tc_built.items():
            self.print_variables({"schema": schema, "error": built.error})
            self.assertEqual(
                built.content_json,
                self.parameters.RICH_JSON,
                msg=f"{self.parameters.MSG_RICH_JSON}: {schema}",
                abort_on_fail=False,
            )
            self.assertEqual(
                built.content_html,
                self.parameters.RICH_HTML,
                msg=f"{self.parameters.MSG_RICH_HTML}: {schema}",
                abort_on_fail=False,
            )
