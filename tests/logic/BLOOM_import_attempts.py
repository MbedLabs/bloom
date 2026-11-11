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
        busy_project, limited_project = (
            self.bloom.bloom_create_project(prefix) for prefix in self.parameters.IMPORT_PREFIXES
        )
        busy_user, limited_user = (
            self.bloom.bloom_add_user(email, role) for email in self.parameters.IMPORT_USERS
        )
        self.tc_first = self.bloom.bloom_begin_import(busy_user, busy_project)
        self.tc_second = self.bloom.bloom_begin_import(busy_user, busy_project)
        self.bloom.bloom_finish_import(self.tc_first.id, self.parameters.IMPORT_COMPLETED)
        self.bloom.bloom_limit_imports(self.parameters.IMPORT_STARTS_ALLOWED)
        self.tc_allowed = []
        for _ in range(self.parameters.IMPORT_STARTS_ALLOWED):
            start = self.bloom.bloom_begin_import(limited_user, limited_project)
            self.tc_allowed.append(start)
            self.bloom.bloom_finish_import(start.id, self.parameters.IMPORT_COMPLETED)
        self.tc_limited = self.bloom.bloom_begin_import(limited_user, limited_project)
        self.tc_recorded = self.bloom.bloom_count_imports(limited_user)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ImportAttemptsTest().run()
