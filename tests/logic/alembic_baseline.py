"""
* @file     ${tests/logic/alembic_baseline.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that the migration chain stays one explicit-DDL baseline.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the alembic baseline.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class AlembicBaselineBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_the_baseline_is_the_only_root(self):
        sources = self.bloom.bloom_revision_sources()
        roots = [
            name
            for name, text in sources.items()
            if any(marker in text for marker in self.parameters.ABL_ROOT_MARKERS)
        ]
        self.print_variables({"roots": roots})
        self.assertEqual(
            roots,
            [self.parameters.ABL_BASELINE],
            msg=self.parameters.MSG_ABL_ROOT,
            abort_on_fail=False,
        )

    def bud_every_later_revision_names_a_parent(self):
        sources = self.bloom.bloom_revision_sources()
        for name, text in sources.items():
            if name != self.parameters.ABL_BASELINE:
                self.assertEqual(
                    ("down_revision = " in text, "down_revision = None" in text),
                    (True, False),
                    msg=self.parameters.MSG_ABL_PARENT.format(name=name),
                    abort_on_fail=False,
                )

    def bud_no_later_revision_rebuilds_the_schema_from_the_models(self):
        sources = self.bloom.bloom_revision_sources()
        for name, text in sources.items():
            if name != self.parameters.ABL_BASELINE:
                self.assertNotIn(
                    "create_all",
                    text,
                    msg=self.parameters.MSG_ABL_NO_CREATE_ALL.format(name=name),
                    abort_on_fail=False,
                )

    def bud_the_baseline_keeps_the_deployed_head_id(self):
        baseline = self.bloom.bloom_revision_sources()[self.parameters.ABL_BASELINE]
        self.assertEqual(
            (
                f'revision: str = "{self.parameters.ABL_HEAD}"' in baseline,
                self.parameters.ABL_ROOT_MARKERS[0] in baseline,
            ),
            (True, True),
            msg=self.parameters.MSG_ABL_HEAD,
            abort_on_fail=False,
        )

    def bud_the_baseline_uses_explicit_ddl(self):
        baseline = self.bloom.bloom_revision_sources()[self.parameters.ABL_BASELINE]
        calls = self.bloom.bloom_create_all_calls(baseline)
        self.print_variables({"create_all calls": calls})
        self.assertEqual(
            (calls, "op.create_table(" in baseline),
            ([], True),
            msg=self.parameters.MSG_ABL_EXPLICIT,
            abort_on_fail=False,
        )

    def bud_the_baseline_creates_the_core_tables(self):
        baseline = self.bloom.bloom_revision_sources()[self.parameters.ABL_BASELINE]
        for table in self.parameters.ABL_CORE_TABLES:
            self.assertIn(
                f'"{table}"',
                baseline,
                msg=self.parameters.MSG_ABL_TABLE.format(table=table),
                abort_on_fail=False,
            )

    def bud_the_baseline_keeps_indexes_the_models_do_not_declare(self):
        baseline = self.bloom.bloom_revision_sources()[self.parameters.ABL_BASELINE]
        for index in self.parameters.ABL_KEPT_INDEXES:
            self.assertIn(
                index,
                baseline,
                msg=self.parameters.MSG_ABL_INDEX.format(index=index),
                abort_on_fail=False,
            )

    def bud_the_baseline_drops_enum_types_on_downgrade(self):
        baseline = self.bloom.bloom_revision_sources()[self.parameters.ABL_BASELINE]
        self.assertIn(
            "DROP TYPE IF EXISTS", baseline, msg=self.parameters.MSG_ABL_ENUMS, abort_on_fail=False
        )
