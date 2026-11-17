"""
* @file     ${tests/pg/visions_migration.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests who holds the Visions policy after the migration.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the Visions migration on PostgreSQL.
"""

from tests.bloom_pg_interface import BloomPgInterface
from tests.bloom_test_base import BloomTestCase


class VisionsMigrationBase(BloomTestCase):

    interface = BloomPgInterface

    def bud_migrations_reach_the_revision_before(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"alembic": self.before[1][-300:]})
        self.assertEqual(
            self.before[0],
            0,
            msg=self.parameters.MSG_MIGRATION_BEFORE,
            abort_on_fail=False,
        )

    def bud_no_visions_policy_exists_before(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.state_before["visions"],
            [],
            msg=self.parameters.MSG_VISIONS_ABSENT,
            abort_on_fail=False,
        )

    def bud_migrations_reach_head(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"alembic": self.upgrade[1][-300:]})
        self.assertEqual(
            self.upgrade[0],
            0,
            msg=self.parameters.MSG_MIGRATION_HEAD,
            abort_on_fail=False,
        )

    def bud_released_maintainer_entry_gains_visions(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"policies": self.after["released"]})
        self.assertEqual(
            self.after["released"],
            sorted((*self.parameters.VISIONS_RELEASED_SET, self.parameters.VISIONS_POLICY)),
            msg=self.parameters.MSG_VISIONS_RELEASED,
            abort_on_fail=False,
        )

    def bud_product_owners_gain_visions(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.print_variables({"policies": self.after["product_owners"]})
        self.assertEqual(
            self.after["product_owners"],
            sorted((*self.state_before["product_owners"], self.parameters.VISIONS_POLICY)),
            msg=self.parameters.MSG_VISIONS_OWNERS,
            abort_on_fail=False,
        )

    def bud_other_holders_are_untouched(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        untouched = self.parameters.VISIONS_UNTOUCHED
        self.print_variables(
            {
                "specifications-only entry": self.after["spec_only"],
                "group": self.after["group"],
            }
        )
        self.assertEqual(
            {key: self.after[key] for key in untouched},
            {key: self.state_before[key] for key in untouched},
            msg=self.parameters.MSG_VISIONS_UNTOUCHED,
            abort_on_fail=False,
        )

    def bud_visions_is_a_default_document_policy(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.after["visions"],
            self.parameters.VISIONS_DEFAULT,
            msg=self.parameters.MSG_VISIONS_DEFAULT,
            abort_on_fail=False,
        )

    def bud_five_policies_are_extended(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            sorted(self.after["covered"]),
            sorted(self.parameters.VISIONS_COVERED),
            msg=self.parameters.MSG_VISIONS_COVERED,
            abort_on_fail=False,
        )

    def bud_extended_policies_treat_visions_as_specifications(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        vision, spec = self.parameters.VISIONS_KIND, self.parameters.VISIONS_SPEC_KIND
        for policy, (permissions, type_tags) in self.after["covered"].items():
            self.print_variables({policy: permissions.get(vision)})
            self.assertEqual(
                (permissions.get(vision), type_tags.get(vision)),
                (permissions[spec], type_tags[spec]),
                msg=self.parameters.MSG_VISIONS_AS_SPEC.format(policy=policy),
                abort_on_fail=False,
            )

    def bud_extended_policies_keep_their_other_permissions(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        vision = self.parameters.VISIONS_KIND
        for policy, (permissions, _) in self.after["covered"].items():
            self.assertEqual(
                {**permissions, vision: None},
                {**self.state_before["covered"][policy][0], vision: None},
                msg=self.parameters.MSG_VISIONS_REST.format(policy=policy),
                abort_on_fail=False,
            )

    def bud_downgrade_over_a_vision_is_refused_naming_the_revision(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.bloom.bloom_run_alembic("downgrade", self.parameters.VISIONS_BEFORE)
        self.print_variables({"alembic": output[-300:]})
        self.assertNotEqual(code, 0, msg=self.parameters.MSG_VISIONS_REFUSED, abort_on_fail=False)
        self.assertIn(
            self.parameters.VISIONS_REFUSAL,
            output,
            msg=self.parameters.MSG_VISIONS_REFUSAL_TEXT,
            abort_on_fail=False,
        )

    def bud_downgrade_without_a_vision_reaches_the_revision_before(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.bloom.bloom_delete_document(self.vision)
        code, output = self.bloom.bloom_run_alembic("downgrade", self.parameters.VISIONS_BEFORE)
        self.print_variables({"alembic": output[-300:]})
        self.assertEqual(code, 0, msg=self.parameters.MSG_MIGRATION_DOWNGRADE, abort_on_fail=False)

    def bud_downgrade_restores_every_row(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        self.assertEqual(
            self.bloom.bloom_read_visions_state(self.seeded),
            self.state_before,
            msg=self.parameters.MSG_VISIONS_DOWNGRADED,
            abort_on_fail=False,
        )

    def bud_migrations_reach_head_a_second_time(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        code, output = self.bloom.bloom_run_alembic("upgrade", self.parameters.MIGRATION_HEAD)
        self.print_variables({"alembic": output[-300:]})
        self.assertEqual(code, 0, msg=self.parameters.MSG_MIGRATION_HEAD_AGAIN, abort_on_fail=False)

    def bud_second_upgrade_gives_the_released_entry_the_same_policies(self):
        if not self.postgres:
            self.skipAssert(self.parameters.MSG_NEEDS_POSTGRES)
            return
        again = self.bloom.bloom_read_visions_state(self.seeded)
        self.assertEqual(
            again["released"],
            self.after["released"],
            msg=self.parameters.MSG_VISIONS_AGAIN,
            abort_on_fail=False,
        )
