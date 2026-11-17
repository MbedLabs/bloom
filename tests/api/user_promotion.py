"""
* @file     ${tests/api/user_promotion.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests who may promote users to admin and that admins stay admins.
* @author   Amine El Omari
* @date     2026-11-13
* @version  1.0.0
* @note     Base class containing the bud methods of the user promotion rules.
"""

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class UserPromotionBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_accounts_are_prepared(self):
        self.print_variables({"sign-ins": self.sign_ins, "created": self.created})
        for status in self.sign_ins:
            self.assertEqual(
                status,
                self.parameters.STATUS_OK,
                msg=self.parameters.MSG_PROMOTION_SIGN_IN,
                abort_on_fail=False,
            )
        for status in self.created:
            self.assertIn(
                status,
                self.parameters.PROMOTION_CREATED,
                msg=self.parameters.MSG_PROMOTION_CREATED,
                abort_on_fail=False,
            )

    def bud_initial_admin_promotes_a_maintainer(self):
        promoted = self.bloom.bloom_api_set_role(
            self.seed, self.maintainer_id, self.parameters.PROMOTION_ADMIN
        )
        body = promoted.body or {}
        self.print_variables({"status": promoted.status, "role": body.get("role")})
        self.assertEqual(
            promoted.status,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_PROMOTION_DONE,
            abort_on_fail=False,
        )
        self.assertEqual(
            body.get("role"),
            self.parameters.PROMOTION_ADMIN,
            msg=self.parameters.MSG_PROMOTION_ROLE,
            abort_on_fail=False,
        )

    def bud_other_admin_cannot_promote(self):
        other = self.bloom.bloom_api_set_role(
            self.other_admin, self.target_id, self.parameters.PROMOTION_ADMIN
        )
        detail = str((other.body or {}).get("detail"))
        self.print_variables({"status": other.status, "detail": detail})
        self.assertEqual(
            other.status,
            self.parameters.STATUS_FORBIDDEN,
            msg=self.parameters.MSG_PROMOTION_REFUSED,
            abort_on_fail=False,
        )
        self.assertIn(
            self.parameters.PROMOTION_ONLY_SEED,
            detail,
            msg=self.parameters.MSG_PROMOTION_REFUSAL_TEXT,
            abort_on_fail=False,
        )

    def bud_admin_cannot_be_demoted(self):
        demoted = self.bloom.bloom_api_set_role(
            self.seed, self.second_admin_id, self.parameters.PROMOTION_MAINTAINER
        )
        detail = str((demoted.body or {}).get("detail"))
        self.print_variables({"status": demoted.status, "detail": detail})
        self.assertEqual(
            demoted.status,
            self.parameters.STATUS_BAD_REQUEST,
            msg=self.parameters.MSG_DEMOTION_REFUSED,
            abort_on_fail=False,
        )
        self.assertIn(
            self.parameters.PROMOTION_ADMIN_FIXED,
            detail,
            msg=self.parameters.MSG_DEMOTION_REFUSAL_TEXT,
            abort_on_fail=False,
        )
