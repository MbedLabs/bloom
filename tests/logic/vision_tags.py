"""
* @file     ${tests/logic/vision_tags.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that a Vision takes and hosts tags and is filed by the Markdown import.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of vision tags and vision import.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class VisionTagsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_a_vision_tags_and_is_tagged(self):
        values = self.parameters
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_markdown_project()
        vision = self.bloom.bloom_add_record(
            "Document", project_id=seeded.project, **values.VIST_VISION
        )
        requirement = self.bloom.bloom_add_record(
            "Requirement", project_id=seeded.project, **values.VIST_REQUIREMENT
        )
        outgoing = self.bloom.bloom_sync_tag_links(
            seeded.project, "VIS", vision, self.bloom.bloom_mention("REQ", requirement)
        )
        incoming = self.bloom.bloom_sync_tag_links(
            seeded.project, "REQ", requirement, self.bloom.bloom_mention("VIS", vision)
        )
        self.assertEqual(
            (outgoing.created, incoming.created, sorted(self.bloom.bloom_list_links())),
            (1, 1, [("REQ", "VIS", "references"), ("VIS", "REQ", "references")]),
            msg=values.MSG_VIST_TAGS,
            abort_on_fail=False,
        )

    def bud_a_markdown_vis_section_is_filed_as_a_vision(self):
        values = self.parameters
        self.bloom.bloom_new_database()
        seeded = self.bloom.bloom_seed_markdown_project()
        self.assertEqual(
            (self.bloom.bloom_markdown_type("vis"), self.bloom.bloom_markdown_type("Vision")),
            ("VIS", "VIS"),
            msg=values.MSG_VIST_NAMES,
            abort_on_fail=False,
        )
        self.bloom.bloom_import_markdown(seeded.project, seeded.admin, values.VIST_MARKDOWN)
        vision = self.bloom.bloom_artefact_titled("Document", "North star")
        self.assertEqual(
            (vision.doc_id, vision.doc_type, vision.status),
            ("PRJ-VIS-001", "VIS", "Draft"),
            msg=values.MSG_VIST_IMPORT,
            abort_on_fail=False,
        )
