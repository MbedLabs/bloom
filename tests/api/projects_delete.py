"""
* @file     ${tests/api/projects_delete.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests deleting a project over the API.
* @author   Amine El Omari
* @date     2026-11-10
* @version  1.0.0
* @note     Base class containing the bud methods of the project delete.
"""

from types import SimpleNamespace

from tests.bloom_api_interface import BloomApiInterface
from tests.bloom_test_base import BloomTestCase


class ProjectsDeleteBase(BloomTestCase):

    interface = BloomApiInterface

    def bud_admin_signs_in(self):
        self.print_variables({"login": self.login})
        self.assertEqual(
            self.login,
            self.parameters.STATUS_OK,
            msg=self.parameters.MSG_DELETE_SIGN_IN,
            abort_on_fail=False,
        )

    def bud_deleted_project_is_gone(self):
        self._assert_deleted(self._delete(self.admin, self.plain_id))

    def bud_project_with_a_requirement_is_deleted(self):
        self.print_variables({"requirement": self.requirement.status_code})
        self.assertEqual(
            self.requirement.status_code,
            self.parameters.STATUS_CREATED,
            msg=self.parameters.MSG_DELETE_REQUIREMENT,
            abort_on_fail=False,
        )
        self._assert_deleted(self._delete(self.admin, self.with_requirement_id))

    def bud_delete_needs_a_signed_in_user(self):
        anonymous = self.bloom.bloom_api_delete_project(None, self.protected_id).status_code
        self.print_variables({"anonymous delete": anonymous})
        self.assertEqual(
            anonymous,
            self.parameters.STATUS_UNAUTHORIZED,
            msg=self.parameters.MSG_DELETE_UNAUTHENTICATED,
            abort_on_fail=False,
        )

    def _delete(self, headers, project_id):
        """Delete the project and read it back, returning both answers' status codes."""
        delete = self.bloom.bloom_api_delete_project(headers, project_id)
        read = self.bloom.bloom_api_get_project(headers, project_id)
        return SimpleNamespace(delete=delete.status_code, read=read.status_code)

    def _assert_deleted(self, outcome):
        """Assert the delete answered 204 and the project then answers 404."""
        self.print_variables({"delete": outcome.delete, "read after": outcome.read})
        self.assertEqual(
            outcome.delete,
            self.parameters.STATUS_NO_CONTENT,
            msg=self.parameters.MSG_DELETE_ANSWER,
            abort_on_fail=False,
        )
        self.assertEqual(
            outcome.read,
            self.parameters.STATUS_NOT_FOUND,
            msg=self.parameters.MSG_DELETE_GONE,
            abort_on_fail=False,
        )
