"""
* @file     ${tests/logic/container_start.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that the image prepares as root and runs everything as appuser.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the container start.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class ContainerStartBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_start_script_hands_supervisord_to_appuser(self):
        handover = self.parameters.START_HANDOVER
        self.print_variables({"last line": self.tc_start_lines[-1:]})
        self.assertEqual(
            self.tc_start_lines[-1:],
            [handover],
            msg=self.parameters.MSG_START_LAST,
            abort_on_fail=False,
        )
        self.assertEqual(
            self.tc_start_lines.count(handover),
            self.parameters.START_HANDOVERS,
            msg=self.parameters.MSG_START_ONCE,
            abort_on_fail=False,
        )
        self.assertIn(
            self.parameters.START_APP_USER,
            self.tc_start_lines,
            msg=self.parameters.MSG_START_APP_USER,
            abort_on_fail=False,
        )

    def bud_start_script_makes_output_writable_for_appuser(self):
        for needle in (
            self.parameters.START_FD_LOOP,
            self.parameters.START_FD_TEST,
            self.parameters.START_FD_CHOWN,
        ):
            self._assert_contains(self.tc_start, needle, self.parameters.MSG_START_FD)
        self._assert_before(
            self.tc_start,
            self.parameters.START_FD_LOOP,
            self.parameters.START_HANDOVER,
            self.parameters.MSG_START_FD_FIRST,
        )

    def bud_start_script_chowns_cloudron_data_recursively(self):
        recursive = self.parameters.START_DATA_CHOWN
        self._assert_contains(self.tc_cloudron, recursive, self.parameters.MSG_START_DATA)
        for later in (self.parameters.START_SECRETS, self.parameters.START_MIGRATION):
            self._assert_before(
                self.tc_cloudron, recursive, later, self.parameters.MSG_START_DATA_FIRST
            )

    def bud_start_script_keeps_the_local_attachment_chown(self):
        self._assert_contains(
            self.tc_local, self.parameters.START_ATTACHMENT_CHOWN, self.parameters.MSG_START_LOCAL
        )
        self._assert_lacks(
            self.tc_local, self.parameters.START_RECURSIVE, self.parameters.MSG_START_LOCAL_FLAT
        )

    def bud_supervisord_does_not_run_as_root(self):
        self.print_variables({"lines": self.tc_supervisord[:6]})
        self.assertNotIn(
            self.parameters.START_ROOT_SETTING,
            self.tc_supervisord,
            msg=self.parameters.MSG_START_NOT_ROOT,
            abort_on_fail=False,
        )
        self.assertIn(
            self.parameters.START_PIDFILE,
            self.tc_supervisord,
            msg=self.parameters.MSG_START_PIDFILE,
            abort_on_fail=False,
        )

    def bud_image_starts_as_root_without_nginx_user(self):
        user_lines = "\n".join(line for line in self.tc_dockerfile.splitlines() if "USER" in line)
        self.assertRegex(
            user_lines,
            self.parameters.START_USER_ROOT,
            msg=self.parameters.MSG_START_USER_ROOT,
            abort_on_fail=False,
        )
        self._assert_lacks(
            self.tc_dockerfile,
            self.parameters.START_NGINX_USER,
            self.parameters.MSG_START_NGINX_USER,
        )
        self._assert_contains(
            self.tc_dockerfile,
            self.parameters.START_NGINX_USER_DROP,
            self.parameters.MSG_START_NGINX_DROP,
        )

    def _assert_contains(self, text, needle, message):
        """Assert the text holds the needle, showing the lines that hold it."""
        lines = "\n".join(line for line in text.splitlines() if needle in line)
        self.assertIn(needle, lines, msg=message, abort_on_fail=False)

    def _assert_lacks(self, text, needle, message):
        """Assert the text does not hold the needle, showing the lines that hold it."""
        lines = "\n".join(line for line in text.splitlines() if needle in line)
        self.assertNotIn(needle, lines, msg=message, abort_on_fail=False)

    def _assert_before(self, text, first, second, message):
        """Assert both strings are in the text and the first comes before the second."""
        positions = (text.find(first), text.find(second))
        self.assertTrue(
            -1 not in positions and positions[0] < positions[1],
            msg=message,
            expected="first before second",
            actual=positions,
            abort_on_fail=False,
        )
