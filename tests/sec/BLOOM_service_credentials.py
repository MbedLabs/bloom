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
        self.admin = self.bloom.bloom_add_admin(
            self.parameters.SERVICE_ADMIN_EMAIL, self.parameters.API_PASSWORD
        )
        self.credential = self.bloom.bloom_create_service_credential(
            self.admin, self.parameters.SERVICE_NAME
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ServiceCredentialsTest().run()
