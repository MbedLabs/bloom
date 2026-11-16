"""
* @file     ${tests/logic/related_docs_filter.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests filtering documents to those linked with one document.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the related documents filter.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class RelatedDocsFilterBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_a_readable_id_resolves_to_its_type_and_row(self):
        self.assertEqual(
            self.bloom.bloom_resolve_doc(self.docs.project, self.parameters.RDF_ANCHOR),
            ("REQ", self.docs.anchor),
            msg=self.parameters.MSG_RDF_RESOLVE,
            abort_on_fail=False,
        )

    def bud_an_unknown_id_resolves_to_nothing(self):
        self.assertEqual(
            self.bloom.bloom_resolve_doc(self.docs.project, self.parameters.RDF_UNKNOWN),
            None,
            msg=self.parameters.MSG_RDF_UNKNOWN,
            abort_on_fail=False,
        )

    def bud_related_artefacts_cover_both_directions(self):
        related = self.bloom.bloom_related_keys(self.docs.project, ("REQ", self.docs.anchor))
        self.print_variables({"related": related})
        self.assertEqual(
            (related, ("REQ", self.docs.other) in related),
            ({("TC", self.docs.verifying), ("TC", self.docs.covering)}, False),
            msg=self.parameters.MSG_RDF_BOTH,
            abort_on_fail=False,
        )

    def bud_related_artefacts_narrow_to_one_role(self):
        related = self.bloom.bloom_related_keys(
            self.docs.project, ("REQ", self.docs.anchor), "verifies"
        )
        self.assertEqual(
            related,
            {("TC", self.docs.verifying)},
            msg=self.parameters.MSG_RDF_ROLE,
            abort_on_fail=False,
        )

    def bud_related_artefacts_narrow_to_one_direction(self):
        for direction, expected in (("outgoing", "verifying"), ("incoming", "covering")):
            related = self.bloom.bloom_related_keys(
                self.docs.project, ("REQ", self.docs.anchor), None, direction
            )
            self.assertEqual(
                related,
                {("TC", getattr(self.docs, expected))},
                msg=self.parameters.MSG_RDF_DIRECTION.format(
                    direction=direction, expected=expected
                ),
                abort_on_fail=False,
            )

    def bud_a_document_without_links_has_no_related_artefacts(self):
        self.assertEqual(
            self.bloom.bloom_related_keys(self.docs.project, ("REQ", self.docs.other)),
            set(),
            msg=self.parameters.MSG_RDF_NONE,
            abort_on_fail=False,
        )

    def bud_links_do_not_reach_across_projects(self):
        other_project = self.bloom.bloom_create_project(self.parameters.RDF_OTHER_PREFIX)
        self.assertEqual(
            self.bloom.bloom_related_keys(other_project, ("REQ", self.docs.anchor)),
            set(),
            msg=self.parameters.MSG_RDF_PROJECT,
            abort_on_fail=False,
        )

    def bud_the_document_list_takes_the_relationship_parameters(self):
        self.assertEqual(
            self.bloom.bloom_docs_list_parameters(),
            self.parameters.RDF_QUERY_PARAMETERS,
            msg=self.parameters.MSG_RDF_PARAMETERS,
            abort_on_fail=False,
        )

    def bud_link_rows_are_scoped_by_project(self):
        self.assertEqual(
            self.bloom.bloom_count_project_links(self.docs.project),
            2,
            msg=self.parameters.MSG_RDF_SCOPED,
            abort_on_fail=False,
        )
