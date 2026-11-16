"""
* @file     ${tests/sec/service_credentials.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests the credential Bud uses to write test results into Bloom.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     Base class containing the bud methods of the service credentials.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ServiceCredentialsBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_service_token_starts_with_its_prefix(self):
        self.print_variables({"token": self.credential.raw[:12]})
        self.assertEqual(
            self.credential.raw[: len(self.parameters.SERVICE_TOKEN_PREFIX)],
            self.parameters.SERVICE_TOKEN_PREFIX,
            msg=self.parameters.MSG_SERVICE_PREFIX,
            abort_on_fail=False,
        )

    def bud_service_credential_is_scoped_to_test_results(self):
        self.assertEqual(
            self.credential.scope,
            self.parameters.SERVICE_SCOPE,
            msg=self.parameters.MSG_SERVICE_SCOPE,
            abort_on_fail=False,
        )

    def bud_stored_hash_does_not_contain_the_token(self):
        self.assertNotIn(
            self.credential.raw,
            self.credential.token_hash,
            msg=self.parameters.MSG_SERVICE_HASH,
            abort_on_fail=False,
        )

    def bud_service_credential_expires_within_90_days(self):
        self.print_variables(
            {"expires": self.credential.expires_at, "limit": self.credential.deadline}
        )
        self.assertLess(
            self.credential.expires_at,
            self.credential.deadline,
            msg=self.parameters.MSG_SERVICE_LIFETIME,
            abort_on_fail=False,
        )

    def bud_service_token_authenticates_as_its_credential(self):
        self.assertEqual(
            self.authenticated,
            (self.credential.id, None),
            msg=self.parameters.MSG_SERVICE_AUTHENTICATES,
            abort_on_fail=False,
        )

    def bud_service_token_is_refused_as_a_user_sign_in(self):
        self.assertEqual(
            self.as_user,
            self.parameters.SERVICE_REFUSED,
            msg=self.parameters.MSG_SERVICE_NOT_A_USER,
            abort_on_fail=False,
        )

    def bud_user_token_without_a_type_is_refused(self):
        self.assertEqual(
            self.untyped,
            self.parameters.SERVICE_REFUSED,
            msg=self.parameters.MSG_SERVICE_UNTYPED,
            abort_on_fail=False,
        )

    def bud_token_of_a_revoked_credential_is_refused(self):
        self.assertEqual(
            self.revoked,
            self.parameters.SERVICE_REFUSED,
            msg=self.parameters.MSG_SERVICE_REVOKED,
            abort_on_fail=False,
        )

    def bud_token_of_an_expired_credential_is_refused(self):
        self.assertEqual(
            self.expired,
            self.parameters.SERVICE_REFUSED,
            msg=self.parameters.MSG_SERVICE_EXPIRED,
            abort_on_fail=False,
        )
