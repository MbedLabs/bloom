"""
* @file     ${tests/logic/BLOOM_import_attempts.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    One ReqIF import runs per project and each user's starts are rate limited.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     This module tests a concurrent start and a start past the user's limit.
"""

from tests.logic.import_attempts import ImportAttemptsBase


class ImportAttemptsTest(ImportAttemptsBase):

    def setUpClass(self):
        super().setUpClass()
        role = self.bloom.bloom_role(self.parameters.IMPORT_ROLE)
        self.busy_project, self.limited_project = (
            self.bloom.bloom_create_project(prefix) for prefix in self.parameters.IMPORT_PREFIXES
        )
        self.busy_user, self.limited_user = (
            self.bloom.bloom_add_user(email, role) for email in self.parameters.IMPORT_USERS
        )

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ImportAttemptsTest().run()
