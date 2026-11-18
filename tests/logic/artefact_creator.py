"""
* @file     ${tests/logic/artefact_creator.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that each artefact records who created it.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the artefact creator record.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ArtefactCreatorBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_every_create_route_records_the_user(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_creator_records()
        self.bloom.bloom_add_requirement_without_creator(records.alpha, *self.parameters.ACR_OLDER)
        self.bloom.bloom_create_one_of_each_artefact(records.alpha, records.ann)
        for kind in self.bloom.bloom_artefact_kinds():
            expected = [None, records.ann] if kind == "Requirement" else [records.ann]
            self.assertEqual(
                self.bloom.bloom_creators(kind),
                expected,
                msg=self.parameters.MSG_ACR_CREATE.format(kind=kind),
                abort_on_fail=False,
            )

    def bud_every_import_records_the_importer(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_creator_records()
        values = self.parameters
        source = self.bloom.bloom_add_requirement_without_creator(records.beta, *values.ACR_SOURCE)
        self.bloom.bloom_run_every_import(
            records.ann,
            records.beta,
            records.alpha,
            [source],
            values.ACR_CSV,
            values.ACR_TESTRAIL,
            values.ACR_MARKDOWN,
        )
        creators = (
            self.bloom.bloom_creators("Requirement", records.alpha),
            self.bloom.bloom_creators("TestCase"),
            self.bloom.bloom_creators("TestSuite"),
            self.bloom.bloom_creators("DesignItem"),
        )
        self.print_variables({"creators": creators})
        self.assertEqual(
            creators,
            ([records.ann], [records.ann, records.ann], [records.ann], [records.ann]),
            msg=values.MSG_ACR_IMPORT,
            abort_on_fail=False,
        )

    def bud_a_jira_defect_records_the_integration_account(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_creator_records()
        for project, email, known in self.parameters.ACR_JIRA_ACCOUNTS:
            expected = records.ann if known else None
            self.assertEqual(
                self.bloom.bloom_new_jira_defect(getattr(records, project), email),
                (expected, expected),
                msg=self.parameters.MSG_ACR_JIRA,
                abort_on_fail=False,
            )

    def bud_a_bud_report_records_the_credential_owner(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_creator_records()
        with_owner, without_owner = self.parameters.ACR_REPORT_RUNS
        self.bloom.bloom_publish_report_as("PRJ", with_owner, records.ann)
        self.bloom.bloom_publish_report_as("PRJ", without_owner, None)
        self.assertEqual(
            self.bloom.bloom_creators("Document"),
            [records.ann, None],
            msg=self.parameters.MSG_ACR_REPORT,
            abort_on_fail=False,
        )

    def bud_deleting_a_user_clears_the_record(self):
        self.bloom.bloom_new_database()
        records = self.bloom.bloom_seed_creator_records()
        self.bloom.bloom_create_one_of_each_artefact(records.alpha, records.ann)
        self.bloom.bloom_delete_user(records.ann, records.admin)
        self.assertEqual(
            (self.bloom.bloom_creators("Requirement"), self.bloom.bloom_creators("Defect")),
            ([None], [None]),
            msg=self.parameters.MSG_ACR_DELETED,
            abort_on_fail=False,
        )

    def bud_no_response_model_carries_the_creator(self):
        self.assertEqual(
            self.bloom.bloom_response_models_with(self.parameters.ACR_FIELD),
            [],
            msg=self.parameters.MSG_ACR_HIDDEN,
            abort_on_fail=False,
        )
