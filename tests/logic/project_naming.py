"""
* @file     ${tests/logic/project_naming.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests project prefixes and the public ids the server alone assigns.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the project naming rules.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ProjectNamingBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_prefix_is_normalized(self):
        prefix = getattr(self.tc_project.instance, "prefix", None)
        self.print_variables({"given": self.parameters.NAMING_PROJECT["prefix"], "stored": prefix})
        self.assertEqual(
            prefix,
            self.parameters.NAMING_PREFIX,
            msg=self.parameters.MSG_NAMING_PREFIX,
            abort_on_fail=False,
        )

    def bud_prefixes_breaking_ids_are_refused(self):
        for prefix, error in self.tc_bad_prefixes.items():
            self.print_variables({"prefix": prefix, "error": error})
            self.assertEqual(
                error,
                self.parameters.NAMING_REFUSAL,
                msg=self.parameters.MSG_NAMING_BAD_PREFIX,
                abort_on_fail=False,
            )

    def bud_update_refuses_an_invalid_prefix(self):
        self.print_variables({"error": self.tc_bad_update.error})
        self.assertEqual(
            self.tc_bad_update.error,
            self.parameters.NAMING_REFUSAL,
            msg=self.parameters.MSG_NAMING_BAD_UPDATE,
            abort_on_fail=False,
        )

    def bud_requirement_create_has_no_client_id(self):
        self._assert_built(self.tc_requirement, self.parameters.NAMING_REQUIREMENT)
        self._assert_no_field("req_id", self.tc_fields["RequirementCreate"])

    def bud_test_case_create_has_no_client_id(self):
        built = self.parameters.NAMING_TEST_CASE
        self._assert_built(self.tc_test_case, {"project_id": built["project_id"]})
        self._assert_no_field("tc_id", self.tc_fields["TestCaseCreate"])

    def bud_document_create_has_no_client_id(self):
        built = self.parameters.NAMING_DOCUMENT
        self._assert_built(self.tc_document, {"doc_type": built["doc_type"]})
        self._assert_no_field("doc_id", self.tc_fields["DocumentCreate"])

    def bud_other_creates_have_no_public_ids(self):
        for name, (field, _) in self.parameters.NAMING_OTHERS.items():
            self._assert_no_field(field, self.tc_fields[name])
            self.print_variables({"schema": name, "error": self.tc_others[name].error})
            self.assertEqual(
                self.tc_others[name].error,
                None,
                msg=self.parameters.MSG_NAMING_BUILDS,
                abort_on_fail=False,
            )

    def _assert_built(self, outcome, expected):
        """Assert each expected field of the built schema holds the given value."""
        for field, value in expected.items():
            actual = getattr(outcome.instance, field, None)
            self.print_variables({"field": field, "value": actual, "error": outcome.error})
            self.assertEqual(
                actual, value, msg=self.parameters.MSG_NAMING_FIELD_KEPT, abort_on_fail=False
            )

    def _assert_no_field(self, field, fields):
        """Assert the schema has no such field."""
        self.assertNotIn(
            field, fields, msg=self.parameters.MSG_NAMING_NO_CLIENT_ID, abort_on_fail=False
        )
