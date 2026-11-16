"""
* @file     ${tests/sec/BLOOM_service_credentials.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    A service token is scoped, stored hashed, never a user sign-in, and dies when revoked or expired.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the service credential functions with one administrator.
"""

from tests.sec.service_credentials import ServiceCredentialsBase


class ServiceCredentialsTest(ServiceCredentialsBase):

    def setUpClass(self):
        super().setUpClass()
        admin = self.bloom.bloom_add_admin(
            self.parameters.SERVICE_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        name = self.parameters.SERVICE_NAME
        self.tc_credential = self.bloom.bloom_create_service_credential(admin, name)
        self.tc_authenticated = self.bloom.bloom_authenticate_service_token(self.tc_credential.raw)
        self.tc_as_user = self.bloom.bloom_sign_in_with_token(self.tc_credential.raw)
        self.tc_untyped = self.bloom.bloom_sign_in_with_token(
            self.bloom.bloom_issue_untyped_token(admin)
        )
        self.bloom.bloom_revoke_service_credential(self.tc_credential.id)
        self.tc_revoked = self.bloom.bloom_authenticate_service_token(self.tc_credential.raw)
        expiring = self.bloom.bloom_create_service_credential(admin, name)
        self.bloom.bloom_expire_service_credential(expiring.id)
        self.tc_expired = self.bloom.bloom_authenticate_service_token(expiring.raw)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ServiceCredentialsTest().run()
