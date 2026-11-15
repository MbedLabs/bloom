"""
* @file     ${tests/sec/nginx_security_headers.py}
* @copyright © EmbedLabs, Aachen ${2026} - all rights reserved
* @brief    This module tests that every nginx location carries the security headers.
* @author   Amine El Omari
* @date     2026-11-11
* @version  1.0.0
* @note     Base class containing the bud methods of the nginx security headers.
"""

from tests.bloom_logic_interface import BloomLogicInterface
from tests.bloom_test_base import BloomTestCase


class NginxSecurityHeadersBase(BloomTestCase):

    interface = BloomLogicInterface

    def bud_shared_file_sets_all_four_headers(self):
        for header in self.parameters.NGINX_REQUIRED_HEADERS:
            self._assert_contains(
                self.tc_headers, f"add_header {header} ", self.parameters.MSG_NGINX_HEADER
            )

    def bud_every_header_is_marked_always(self):
        for line in self.tc_headers.splitlines():
            if line.strip().startswith("add_header"):
                self.print_variables({"line": line.strip()[:80]})
                self.assertTrue(
                    line.rstrip().endswith(self.parameters.NGINX_ALWAYS),
                    msg=self.parameters.MSG_NGINX_ALWAYS,
                    expected=f"ends with {self.parameters.NGINX_ALWAYS}",
                    actual=line.rstrip()[-20:],
                    abort_on_fail=False,
                )

    def bud_server_block_includes_the_shared_file(self):
        self._assert_contains(
            self.tc_server_head,
            self.parameters.NGINX_INCLUDE,
            self.parameters.MSG_NGINX_SERVER_INCLUDE,
        )

    def bud_locations_with_own_headers_include_the_shared_file(self):
        for location, body in self.tc_locations:
            if "add_header" in body:
                self.print_variables({"location": location})
                self._assert_contains(
                    body, self.parameters.NGINX_INCLUDE, self.parameters.MSG_NGINX_LOCATION_INCLUDE
                )

    def bud_content_security_policy_forbids_inline_script(self):
        csp = next(
            (
                line
                for line in self.tc_headers.splitlines()
                if "Content-Security-Policy" in line and "add_header" in line
            ),
            "",
        )
        script_src = csp.split("script-src")[1].split(";")[0] if "script-src" in csp else ""
        self.print_variables({"policy": csp, "script-src": script_src})
        self.assertIn(
            self.parameters.NGINX_SCRIPT_SRC,
            csp,
            msg=self.parameters.MSG_NGINX_SCRIPT_SRC,
            abort_on_fail=False,
        )
        self.assertNotIn(
            self.parameters.NGINX_UNSAFE_INLINE,
            script_src,
            msg=self.parameters.MSG_NGINX_NO_INLINE,
            abort_on_fail=False,
        )
        self.assertIn(
            self.parameters.NGINX_FRAME_ANCESTORS,
            csp,
            msg=self.parameters.MSG_NGINX_FRAMES,
            abort_on_fail=False,
        )

    def bud_image_ships_the_shared_file(self):
        self._assert_contains(
            self.tc_dockerfile, self.parameters.NGINX_IMAGE_COPY, self.parameters.MSG_NGINX_IMAGE
        )

    def _assert_contains(self, text, needle, message):
        """Assert the text holds the needle, showing the lines that hold it."""
        lines = "\n".join(line for line in text.splitlines() if needle.strip() in line)
        self.assertIn(needle, lines, msg=message, abort_on_fail=False)
