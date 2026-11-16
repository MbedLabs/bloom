"""
* @file     ${tests/sec/controlled_artefacts_external_visibility.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests which designs, risks, changes, test concepts and defects an external reader gets.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the controlled artefacts an external reader reads.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ControlledArtefactsExternalVisibilityBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_lists_hold_only_the_customer_artefact(self):
        for (kind, _, field, _), pair, seen in zip(
            self.parameters.CONTROLLED_KINDS, self.tc_pairs, self.tc_seen
        ):
            self.print_variables({"kind": kind, "listed": seen.listed.body})
            self.assertEqual(
                (seen.listed.status, [row[field] for row in seen.listed.body["items"]]),
                (self.parameters.STATUS_OK, [pair.public]),
                msg=self.parameters.MSG_CONTROLLED_LIST.format(kind=kind),
                abort_on_fail=False,
            )

    def bud_internal_artefacts_are_hidden_404(self):
        for (kind, _, field, _), pair, seen in zip(
            self.parameters.CONTROLLED_KINDS, self.tc_pairs, self.tc_seen
        ):
            self.assertEqual(
                seen.hidden.status,
                self.parameters.STATUS_NOT_FOUND,
                msg=self.parameters.MSG_CONTROLLED_HIDDEN.format(kind=kind),
                abort_on_fail=False,
            )

    def bud_customer_artefacts_open_with_their_id_and_visibility(self):
        for (kind, _, field, _), pair, seen in zip(
            self.parameters.CONTROLLED_KINDS, self.tc_pairs, self.tc_seen
        ):
            self.assertEqual(
                (seen.visible.status, seen.visible.body[field], seen.visible.body["visibility"]),
                (self.parameters.STATUS_OK, pair.public, self.parameters.CUSTOMER_VISIBILITY),
                msg=self.parameters.MSG_CONTROLLED_SHOWN.format(kind=kind),
                abort_on_fail=False,
            )
