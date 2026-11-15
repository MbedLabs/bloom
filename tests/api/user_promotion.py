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
        self.print_variables({"sign-ins": self.tc_sign_ins, "created": self.tc_created})
        for status in self.tc_sign_ins:
            self.assertEqual(
                status,
                self.parameters.STATUS_OK,
                msg=self.parameters.MSG_PROMOTION_SIGN_IN,
                abort_on_fail=False,
            )
        for status in self.tc_created:
            self.assertIn(
                status,
                self.parameters.PROMOTION_CREATED,
                msg=self.parameters.MSG_PROMOTION_CREATED,
                abort_on_fail=False,
            )

    def bud_initial_admin_promotes_a_maintainer(self):
        body = self.tc_promoted.body or {}
        self.print_variables({"status": self.tc_promoted.status, "role": body.get("role")})
        self.assertEqual(
            self.tc_promoted.status,
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
        detail = str((self.tc_other.body or {}).get("detail"))
        self.print_variables({"status": self.tc_other.status, "detail": detail})
        self.assertEqual(
            self.tc_other.status,
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
        detail = str((self.tc_demoted.body or {}).get("detail"))
        self.print_variables({"status": self.tc_demoted.status, "detail": detail})
        self.assertEqual(
            self.tc_demoted.status,
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
