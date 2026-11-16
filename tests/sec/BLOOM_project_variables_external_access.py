"""
* @file     ${tests/sec/BLOOM_project_variables_external_access.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    An external reader is refused the project parameters; a member with every permission lists them.
* @author   Amine El Omari
* @date     2026-11-16
* @version  1.0.0
* @note     This module tests the parameters API with one external reader, one full member and one parameter.
"""

from tests.sec.project_variables_external_access import (
    ProjectVariablesExternalAccessBase,
)


class ProjectVariablesExternalAccessTest(ProjectVariablesExternalAccessBase):

    def setUpClass(self):
        super().setUpClass()
        bloom, values = self.bloom, self.parameters
        reader = bloom.bloom_create_external_reader_environment()
        email, password = values.READER_MAINTAINER_EMAIL, values.API_PASSWORD
        member = bloom.bloom_add_account(email, password, values.API_MEMBER_ROLE)
        bloom.bloom_add_internal_member(reader.project_id, member, values.READER_ALL_PERMISSIONS)
        bloom.bloom_add_project_variable(
            reader.project_id, values.READER_VARIABLE_KEY, values.READER_VARIABLE_VALUE
        )
        headers, _ = bloom.bloom_log_in(email, password)
        self.tc_refused = bloom.bloom_api_list_variables(reader.headers, reader.project_id)
        self.tc_listed = bloom.bloom_api_list_variables(headers, reader.project_id)

    def tearDownClass(self):
        super().tearDownClass()


if __name__ == "__main__":
    ProjectVariablesExternalAccessTest().run()
